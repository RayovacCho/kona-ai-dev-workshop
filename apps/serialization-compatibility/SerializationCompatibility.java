import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.nio.file.Path;

/** Cross-JDK Java Object Serialization wire-format compatibility probe. */
public class SerializationCompatibility {
    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !(args[0].equals("write") || args[0].equals("read"))) {
            throw new IllegalArgumentException("usage: write|read <stream-file>");
        }
        Path stream = Path.of(args[1]);
        if (args[0].equals("write")) {
            write(stream);
        } else {
            read(stream);
        }
    }

    private static void write(Path stream) throws IOException {
        SharedGraph graph = new SharedGraph();
        Person shared = new Person(42, "共享对象-Shared");
        graph.people = new Person[] {shared, shared};
        graph.self = graph;
        try (ObjectOutputStream output = new ObjectOutputStream(
                new FileOutputStream(stream.toFile()))) {
            output.writeObject(graph);
            output.writeUnshared(new Person(7, "非共享-Unshared"));
        }
    }

    private static void read(Path stream) throws Exception {
        try (ObjectInputStream input = new ObjectInputStream(
                new FileInputStream(stream.toFile()))) {
            SharedGraph graph = (SharedGraph) input.readObject();
            if (graph.self != graph) {
                throw new RuntimeException("cyclic reference was not preserved");
            }
            if (graph.people.length != 2 || graph.people[0] != graph.people[1]) {
                throw new RuntimeException("shared reference identity was not preserved");
            }
            if (!"共享对象-Shared".equals(graph.people[0].name)) {
                throw new RuntimeException("multilingual field value was corrupted");
            }
            Person unshared = (Person) input.readUnshared();
            if (unshared.id != 7 || !"非共享-Unshared".equals(unshared.name)) {
                throw new RuntimeException("unshared value was corrupted");
            }
            if (input.read() != -1) {
                throw new RuntimeException("unexpected trailing stream data");
            }
        }
    }

    private static final class SharedGraph implements Serializable {
        private static final long serialVersionUID = 1L;

        private Person[] people;
        private SharedGraph self;
    }

    private static final class Person implements Serializable {
        private static final long serialVersionUID = 1L;

        private final int id;
        private final String name;

        private Person(int id, String name) {
            this.id = id;
            this.name = name;
        }
    }
}
