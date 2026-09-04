package workshop.serialization;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.TearDown;
import org.openjdk.jmh.annotations.Warmup;

/** Focused write-path benchmarks that reduce stream and buffer-growth noise. */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(3)
public class SerializationFocusedBenchmark {

    @State(Scope.Thread)
    public static class BenchmarkState {
        @Param({"GRAPH", "GRAPH_CHINESE", "LARGE_OBJECT_ARRAY"})
        public String payloadType;

        private Serializable payload;
        private int serializedSize;
        private ByteArrayOutputStream reusableBytes;
        private ObjectOutputStream reusableOutput;

        @Setup(Level.Trial)
        public void setup() throws IOException {
            payload = payloadType.equals("LARGE_OBJECT_ARRAY")
                    ? createLargeObjectArray()
                    : createGraph(payloadType.equals("GRAPH_CHINESE") ? "成员-" : "person-");
            serializedSize = serialize(payload, 4096).length;
            reusableBytes = new ByteArrayOutputStream(serializedSize);
            reusableOutput = new ObjectOutputStream(reusableBytes);
        }

        @TearDown(Level.Trial)
        public void tearDown() throws IOException {
            reusableOutput.close();
        }
    }

    @Benchmark
    public byte[] serializePreSized(BenchmarkState state) throws IOException {
        return serialize(state.payload, state.serializedSize);
    }

    @Benchmark
    public int serializeSteadyState(BenchmarkState state) throws IOException {
        state.reusableOutput.reset();
        state.reusableOutput.flush();
        state.reusableBytes.reset();
        state.reusableOutput.writeObject(state.payload);
        state.reusableOutput.flush();
        return state.reusableBytes.size();
    }

    private static byte[] serialize(Object value, int initialCapacity) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(initialCapacity);
        try (ObjectOutputStream output = new ObjectOutputStream(bytes)) {
            output.writeObject(value);
        }
        return bytes.toByteArray();
    }

    private static Person[] createGraph(String prefix) {
        Person[] people = new Person[100];
        for (int index = 0; index < people.length; index++) {
            people[index] = new Person(index, prefix + index, index * 1.25d);
        }
        return people;
    }

    private static Person[] createLargeObjectArray() {
        Person[] people = new Person[4096];
        for (int index = 0; index < people.length; index++) {
            String name = (index & 1) == 0 ? "person-" + index : "成员-" + index;
            people[index] = new Person(index, name, index * 1.25d);
        }
        return people;
    }

    private record Person(int id, String name, double score) implements Serializable {
        private static final long serialVersionUID = 1L;
    }
}
