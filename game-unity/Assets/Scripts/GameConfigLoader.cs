using System;
using System.IO;
using UnityEngine;

namespace GameConfig.Runtime
{
    public static class GameConfigLoader
    {
        public static RuntimeContract Load()
        {
            string path = ResolveContractPath();
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("Unity runtime contract was not found.", path);
            }

            RuntimeContract contract = JsonUtility.FromJson<RuntimeContract>(File.ReadAllText(path));
            if (contract == null || contract.configs == null || contract.runtime_scenario == null)
            {
                throw new InvalidDataException("Unity runtime contract is malformed.");
            }
            if (contract.configs.weapon_config == null || contract.configs.weapon_config.Length == 0)
            {
                throw new InvalidDataException("weapon_config must contain at least one row.");
            }
            return contract;
        }

        private static string ResolveContractPath()
        {
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "--config-input");
            return index >= 0 && index + 1 < args.Length
                ? Path.GetFullPath(args[index + 1])
                : Path.Combine(Application.streamingAssetsPath, "game_config.json");
        }
    }
}
