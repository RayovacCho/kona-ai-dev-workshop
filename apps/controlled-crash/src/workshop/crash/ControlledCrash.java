package workshop.crash;

import jdk.test.whitebox.WhiteBox;

/** 有意终止调试版 HotSpot VM，用于崩溃日志实验。 */
public final class ControlledCrash {
    private ControlledCrash() {}

    public static void main(String[] args) {
        if (args.length != 1) {
            usage("必须且只能提供一个崩溃编号");
        }

        final int how;
        try {
            how = Integer.parseInt(args[0]);
        } catch (NumberFormatException e) {
            usage("不是整数：" + args[0]);
            return;
        }

        System.out.printf("正在触发 VMError::controlled_crash(%d)；此 JVM 应当终止。%n", how);
        System.out.flush();
        WhiteBox.getWhiteBox().controlledCrash(how);
        throw new AssertionError("controlledCrash 意外返回");
    }

    private static void usage(String reason) {
        System.err.println("错误：" + reason);
        System.err.println("用法：ControlledCrash <编号>");
        System.err.println("已知编号：1=assert，2=guarantee，14=SIGSEGV，15=SIGFPE，");
        System.err.println("          16=持有 ThreadsListHandle 时触发 fatal，17=持有嵌套 handle 时触发 fatal");
        System.err.println("其他整数会触发通用 fatal 错误。");
        System.exit(2);
    }
}
