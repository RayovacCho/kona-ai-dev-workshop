package workshop.crash;

import jdk.test.whitebox.WhiteBox;

/** Intentionally terminates a debug HotSpot VM for crash-log experiments. */
public final class ControlledCrash {
    private ControlledCrash() {}

    public static void main(String[] args) {
        if (args.length != 1) {
            usage("expected exactly one crash number");
        }

        final int how;
        try {
            how = Integer.parseInt(args[0]);
        } catch (NumberFormatException e) {
            usage("not an integer: " + args[0]);
            return;
        }

        System.out.printf("Triggering VMError::controlled_crash(%d); this JVM should terminate.%n", how);
        System.out.flush();
        WhiteBox.getWhiteBox().controlledCrash(how);
        throw new AssertionError("controlledCrash unexpectedly returned");
    }

    private static void usage(String reason) {
        System.err.println("Error: " + reason);
        System.err.println("Usage: ControlledCrash <number>");
        System.err.println("Known numbers: 1=assert, 2=guarantee, 14=SIGSEGV, 15=SIGFPE,");
        System.err.println("               16=fatal with ThreadsListHandle, 17=fatal with nested handle");
        System.err.println("Other integers trigger a generic fatal error.");
        System.exit(2);
    }
}
