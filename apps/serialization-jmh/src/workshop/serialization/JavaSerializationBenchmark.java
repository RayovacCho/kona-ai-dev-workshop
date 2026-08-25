package workshop.serialization;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.util.ArrayList;
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
        @Param({"SMALL", "GRAPH", "CUSTOM"})
        public String payloadType;

        private Serializable payload;
        private byte[] serialized;

        @Setup
        public void setup() throws IOException {
            payload = switch (payloadType) {
                case "SMALL" -> new Person(42, "Ada", true, 98.5d);
                case "GRAPH" -> createGraph();
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
            if (restored.getClass() != payload.getClass()) {
                throw new IllegalStateException("Round-trip type mismatch for " + payloadType);
            }
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
        List<Person> people = new ArrayList<>(100);
        for (int index = 0; index < 100; index++) {
            people.add(new Person(index, "person-" + index, (index & 1) == 0, index * 1.25d));
        }
        return new Graph("team", people, new int[] {1, 2, 3, 5, 8, 13, 21});
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
