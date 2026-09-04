package workshop.serialization;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;
import org.openjdk.jmh.infra.Blackhole;

/** Baseline for the built-in java.io object serialization implementation. */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(3)
public class JavaSerializationBenchmark {

    @State(Scope.Thread)
    public static class BenchmarkState {
        @Param({
                "SMALL",
                "SMALL_CHINESE",
                "GRAPH",
                "GRAPH_CHINESE",
                "LARGE_OBJECT_ARRAY",
                "CUSTOM"
        })
        public String payloadType;

        private Serializable payload;
        private byte[] serialized;

        @Setup
        public void setup() throws IOException {
            payload = switch (payloadType) {
                case "SMALL" -> new Person(42, "Ada", true, 98.5d);
                case "SMALL_CHINESE" -> new Person(42, "艾达", true, 98.5d);
                case "GRAPH" -> createGraph();
                case "GRAPH_CHINESE" -> createChineseGraph();
                case "LARGE_OBJECT_ARRAY" -> createLargeObjectArray();
                case "CUSTOM" -> new CustomData(42, "Kona serialization benchmark");
                default -> throw new IllegalArgumentException("Unknown payload type: " + payloadType);
            };
            serialized = serialize(payload);
            Object restored;
            try {
                restored = deserialize(serialized);
            } catch (ClassNotFoundException exception) {
                throw new IOException("Benchmark payload cannot be deserialized", exception);
            }
            verifyRoundTrip(payloadType, payload, restored);
        }
    }

    @Benchmark
    public byte[] serialize(BenchmarkState state) throws IOException {
        return serialize(state.payload);
    }

    @Benchmark
    public Object deserialize(BenchmarkState state) throws IOException, ClassNotFoundException {
        return deserialize(state.serialized);
    }

    @Benchmark
    public Object roundTrip(BenchmarkState state, Blackhole blackhole)
            throws IOException, ClassNotFoundException {
        byte[] bytes = serialize(state.payload);
        blackhole.consume(bytes);
        return deserialize(bytes);
    }

    private static byte[] serialize(Object value) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(4096);
        try (ObjectOutputStream output = new ObjectOutputStream(bytes)) {
            output.writeObject(value);
        }
        return bytes.toByteArray();
    }

    private static Object deserialize(byte[] bytes) throws IOException, ClassNotFoundException {
        try (ObjectInputStream input = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
            return input.readObject();
        }
    }

    private static Graph createGraph() {
        return createGraph("team", "person-");
    }

    private static Graph createChineseGraph() {
        return createGraph("团队", "成员-");
    }

    private static Graph createGraph(String graphName, String personNamePrefix) {
        List<Person> people = new ArrayList<>(100);
        for (int index = 0; index < 100; index++) {
            people.add(new Person(
                    index,
                    personNamePrefix + index,
                    (index & 1) == 0,
                    index * 1.25d));
        }
        return new Graph(graphName, people, new int[] {1, 2, 3, 5, 8, 13, 21});
    }

    private static Person[] createLargeObjectArray() {
        Person[] people = new Person[4096];
        for (int index = 0; index < people.length; index++) {
            String name = (index & 1) == 0 ? "person-" + index : "成员-" + index;
            people[index] = new Person(index, name, (index & 1) == 0, index * 1.25d);
        }
        return people;
    }

    private static void verifyRoundTrip(String payloadType, Object expected, Object actual) {
        boolean matches = switch (payloadType) {
            case "SMALL", "SMALL_CHINESE" -> expected.equals(actual);
            case "GRAPH", "GRAPH_CHINESE" -> graphEquals((Graph) expected, (Graph) actual);
            case "LARGE_OBJECT_ARRAY" -> Arrays.equals((Person[]) expected, (Person[]) actual);
            case "CUSTOM" -> customDataEquals((CustomData) expected, (CustomData) actual);
            default -> false;
        };
        if (!matches) {
            throw new IllegalStateException("Round-trip content mismatch for " + payloadType);
        }
    }

    private static boolean graphEquals(Graph expected, Graph actual) {
        return expected.name().equals(actual.name())
                && expected.people().equals(actual.people())
                && Arrays.equals(expected.weights(), actual.weights());
    }

    private static boolean customDataEquals(CustomData expected, CustomData actual) {
        return expected.number == actual.number && expected.text.equals(actual.text);
    }

    private record Person(int id, String name, boolean active, double score)
            implements Serializable {
        private static final long serialVersionUID = 1L;
    }

    private record Graph(String name, List<Person> people, int[] weights)
            implements Serializable {
        private static final long serialVersionUID = 1L;
    }

    private static final class CustomData implements Serializable {
        private static final long serialVersionUID = 1L;

        private transient int number;
        private transient String text;

        private CustomData(int number, String text) {
            this.number = number;
            this.text = text;
        }

        private void writeObject(ObjectOutputStream output) throws IOException {
            output.writeInt(number);
            output.writeUTF(text);
        }

        private void readObject(ObjectInputStream input) throws IOException {
            number = input.readInt();
            text = input.readUTF();
        }
    }
}
