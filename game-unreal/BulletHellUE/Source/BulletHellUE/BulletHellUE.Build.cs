using UnrealBuildTool;

public class BulletHellUE : ModuleRules
{
    public BulletHellUE(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "Json",
            "JsonUtilities",
            "RenderCore"
        });
        PublicSystemLibraries.Add("bcrypt.lib");
    }
}
