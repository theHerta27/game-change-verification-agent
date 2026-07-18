using System;

namespace GameConfig.Runtime
{
    public sealed class RuntimeRunSettings
    {
        public const int DefaultSeed = 20260718;

        public bool AutoRun { get; private set; }
        public int RandomSeed { get; private set; }
        public string RunMode => AutoRun ? "auto" : "manual";

        public static RuntimeRunSettings FromArgs(string[] args)
        {
            RuntimeRunSettings settings = new()
            {
                AutoRun = Array.IndexOf(args, "--auto-run") >= 0,
                RandomSeed = DefaultSeed,
            };

            int seedIndex = Array.IndexOf(args, "--seed");
            if (seedIndex < 0) return settings;
            if (seedIndex + 1 >= args.Length || !int.TryParse(args[seedIndex + 1], out int seed))
                throw new ArgumentException("--seed requires a valid 32-bit integer.");
            settings.RandomSeed = seed;
            return settings;
        }
    }
}
