import unreal


PRESENTATION_PATH = "/Game/Presentation"
MAP_PATH = "/Game/Maps/BulletHellDemo"
BLUEPRINT_NAMES = (
    "BP_ArenaView",
    "BP_PlayerView",
    "BP_BossView",
    "BP_ProjectileFieldView",
)


def ensure_blueprint(name: str) -> None:
    asset_path = f"{PRESENTATION_PATH}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.log(f"Presentation asset already exists: {asset_path}")
        return

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    blueprint = asset_tools.create_asset(name, PRESENTATION_PATH, unreal.Blueprint, factory)
    if blueprint is None:
        raise RuntimeError(f"Failed to create Blueprint: {asset_path}")
    unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
    unreal.log(f"Created presentation Blueprint: {asset_path}")


def ensure_level() -> None:
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        unreal.log(f"Runtime level already exists: {MAP_PATH}")
        return
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not subsystem.new_level(MAP_PATH):
        raise RuntimeError(f"Failed to create runtime level: {MAP_PATH}")
    if not subsystem.save_current_level():
        raise RuntimeError(f"Failed to save runtime level: {MAP_PATH}")
    unreal.log(f"Created runtime level: {MAP_PATH}")


for blueprint_name in BLUEPRINT_NAMES:
    ensure_blueprint(blueprint_name)
ensure_level()
unreal.EditorAssetLibrary.save_directory("/Game")
unreal.log("Bullet Hell Blueprint presentation assets are ready.")
