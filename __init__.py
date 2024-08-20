import os
import pickle
from typing import ClassVar, Dict, List, Optional, Sequence, Tuple
from ..AutoWorld import WebWorld, World
from BaseClasses import CollectionState, Item, ItemClassification, Location, LocationProgressType, MultiWorld, \
    Region, Tutorial
from Fill import fill_restrictive, sweep_from_pool
from settings import Group, UserFilePath
from worlds.LauncherComponents import Component, SuffixIdentifier, Type, components, launch_subprocess
from worlds.generic.Rules import set_rule
from .Items import ALBWItem, Items, ItemData, ItemType, all_items, item_table, vane_to_item, \
    convenient_hyrule_vanes, convenient_lorule_vanes, hyrule_vanes, lorule_vanes
from .Locations import ALBWLocation, LocationData, LocationType, all_locations, dungeon_table, location_table, \
    dungeon_item_excludes
from .Options import ALBWOptions, CrackShuffle, InitialCrackState, Keysy, LogicMode, NiceItems, WeatherVanes, \
    create_randomizer_settings
from .Patch import PatchInfo, ALBWProcedurePatch
from albwrandomizer import ArchipelagoInfo, PyRandomizable, SeedInfo, randomize_pre_fill

albw_base_id = 6242624000

def launch_client(*args):
    from .Client import launch
    launch_subprocess(launch, name="ALBWClient")

components.append(
    Component(
        "A Link Between Worlds Client",
        func=launch_client,
        component_type=Type.CLIENT,
        file_identifier=SuffixIdentifier(".apalbw")
    )
)

class ALBWWebWorld(WebWorld):
    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to playing A Link Between Worlds with Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["randomsalience"],
    )

    tutorials = [setup_en]

class ALBWSettings(Group):
    class ALBWRomFile(UserFilePath):
        """File name of your decrypted North American A Link Between Worlds ROM"""
        description = "A Link Between Worlds ROM File"
        
        @classmethod
        def validate(cls, path: str) -> None:
            pass #TODO add validation; hashing doesn't work for 3ds roms

    rom_file: ALBWRomFile = ALBWRomFile("Legend of Zelda, The - A Link Between Worlds (USA) (En,Fr,Es).3ds")

class ALBWWorld(World):
    """
    A Link Between Worlds is a game in the classic Legend of Zelda series,
    and a sequel to A Link to the Past. Explore dungeons, fight monsters,
    discover magical items, and save the worlds of Hyrule and Lorule!
    """
    game: ClassVar[str] = "A Link Between Worlds"
    options_dataclass = ALBWOptions
    options: ALBWOptions
    topology_present: ClassVar[bool] = False
    required_client_version: Tuple[int, int, int] = (0, 5, 0)
    web: ClassVar[WebWorld] = ALBWWebWorld()
    settings: ALBWSettings
    settings_key: ClassVar[str] = "albw_settings"

    item_name_to_id: ClassVar[Dict[str, int]] = \
        {item.name: item.code + albw_base_id for item in all_items if item.code is not None}
    location_name_to_id: ClassVar[Dict[str, int]] = \
        {loc.name: loc.code + albw_base_id for loc in all_locations if loc.code is not None}

    itempool: List[Item]
    pre_fill_items: List[Item]
    starting_weapon: Optional[ItemData]

    seed: Optional[int]
    seed_info: Optional[SeedInfo]

    def create_item(self, name: str) -> ALBWItem:
        item_id = self.item_name_to_id[name] if name in self.item_name_to_id else None
        return ALBWItem(name, item_table[name].get_classification(self.options), item_id, self.player)
    
    def create_location(self, name: str, region: Region) -> ALBWLocation:
        loc_id = self.location_name_to_id[name] if name in self.location_name_to_id else None
        return ALBWLocation(self.player, name, loc_id, region)
    
    def get_filler_item_name(self):
        filler_items = []
        for item in all_items:
            if item.itemtype == ItemType.Junk:
                for _ in range(item.count):
                    filler_items.append(item.name)
        return self.random.choice(filler_items)
    
    def generate_early(self) -> None:
        self.seed = self.random.randrange(2**32)
        settings = create_randomizer_settings(self.options)
        archipelago_info = ArchipelagoInfo()
        archipelago_info.name = self.player_name
        self.seed_info = randomize_pre_fill(self.seed, settings, archipelago_info)

        # add starting weather vanes
        starting_vanes = []
        if self.options.weather_vanes in [WeatherVanes.option_hyrule, WeatherVanes.option_all]:
            starting_vanes += hyrule_vanes
        if self.options.weather_vanes in [WeatherVanes.option_lorule, WeatherVanes.option_all]:
            starting_vanes += lorule_vanes
        if self.options.weather_vanes == WeatherVanes.option_convenient:
            starting_vanes += convenient_hyrule_vanes
            if not self.options.crack_shuffle == CrackShuffle.option_off:
                starting_vanes += convenient_lorule_vanes
        for vane in starting_vanes:
            self.options.start_inventory.value[vane.name] = 1
    
    def create_regions(self) -> None:
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu_region)

        assert self.seed_info is not None
        region_graph = self.seed_info.get_region_graph()

        # generate regions and locations
        for (region_name, (locations, _)) in region_graph.items():
            region = Region(region_name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            for location_name in locations:
                # skip locations like hint ghosts without AP counterparts
                if location_name not in location_table:
                    continue

                loc_data = location_table[location_name]
                if self._is_unrandomized(loc_data):
                    continue
                location = self.create_location(location_name, region)

                # exclude Mother Maiamai locations so Maiamai can be filler items
                # if loc_data.loctype == LocationType.Upgrade and self.options.nice_mode:
                #     location.progress_type = LocationProgressType.EXCLUDED
                
                # optionally exclude minigames
                if loc_data.loctype == LocationType.Minigame and self.options.minigames_excluded:
                    location.progress_type = LocationProgressType.EXCLUDED

                # place default item
                item = self._get_location_item(loc_data)
                if item is not None:
                    location.place_locked_item(self.create_item(item.name))

                set_rule(location, lambda state, location_name=location_name:
                    self.seed_info.can_reach(location_name, self._convert_state(state)))
                region.locations.append(location)

        ravio_shop_region = self.multiworld.get_region("RavioShop", self.player)
        menu_region.connect(ravio_shop_region)

        # generate connections
        path_counts = {}
        for (source_region_name, (_, paths)) in region_graph.items():
            for target_region_name in paths:
                source_region = self.multiworld.get_region(source_region_name, self.player)
                target_region = self.multiworld.get_region(target_region_name, self.player)
                name = f"{source_region_name} -> {target_region_name}"
                if name in path_counts.keys():
                    path_counts[name] += 1
                    name = f"{name} [{path_counts[name]}]"
                else:
                    path_counts[name] = 1
                source_region.connect(target_region, name=name, rule=
                    lambda state, source_region_name=source_region_name, target_region_name=target_region_name:
                    self.seed_info.can_traverse(source_region_name, target_region_name, self._convert_state(state)))
    
    def create_items(self) -> None:
        self.itempool = []
        self.pre_fill_items = []
        if self.options.assured_weapon:
            self.starting_weapon = self._get_random_weapon()
        else:
            self.starting_weapon = None
        
        for item in all_items:
            count = self._get_item_count(item)
            if self._save_for_pre_fill(item):
                for _ in range(count):
                    self.pre_fill_items.append(self.create_item(item.name))
                continue
            if item == self.starting_weapon:
                self.pre_fill_items.append(self.create_item(item.name))
                count -= 1
            for _ in range(count):
                self.itempool.append(self.create_item(item.name))
        
        num_items = len(self.itempool) + len(self.pre_fill_items)
        num_locations = len(self.multiworld.get_unfilled_locations(self.player))
        for _ in range(num_locations - num_items):
            self.itempool.append(self.create_filler())
        
        self.random.shuffle(self.itempool)
        self.multiworld.itempool.extend(self.itempool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Triforce", self.player)
    
    def pre_fill(self) -> None:
        # randomize dungeon prizes
        if self.options.randomize_dungeon_prizes:
            prize_itempool = [item for item in self.pre_fill_items if item_table[item.name].itemtype == ItemType.Prize]
            prize_location_names = [loc.name for loc in all_locations if loc.loctype == LocationType.Prize]
            self._initial_fill(prize_itempool, prize_location_names)

        # randomize dungeon items
        for dungeon in dungeon_table:
            dungeon_itempool = [item for item in self.pre_fill_items if item_table[item.name] in dungeon.items]
            if dungeon.name == "Lorule Castle" and self.options.bow_of_light_in_castle:
                dungeon_itempool.append(self.create_item(Items.BowOfLight.name))
            dungeon_location_names = [loc.name for loc in dungeon.locations if loc.name not in dungeon_item_excludes]
            self._initial_fill(dungeon_itempool, dungeon_location_names)
        
        # starting weapon
        if self.starting_weapon is not None:
            starting_weapon_itempool = [item for item in self.pre_fill_items if item.name == self.starting_weapon.name]
            ravio_location_names = [loc.name for loc in all_locations if loc.loctype == LocationType.Ravio]
            self._initial_fill(starting_weapon_itempool, ravio_location_names)
    
    def fill_slot_data(self) -> None:
        return {"seed": self.seed}

    def generate_output(self, output_directory: str) -> None:
        # Create patch info object
        check_map = self._build_check_map()
        item_names = {loc.name: loc.item.name for loc in self.multiworld.get_locations(self.player)}
        patch_info = PatchInfo(PatchInfo.version, self.seed, self.player_name, self.options, check_map, item_names)

        # Write patch info to binary file
        patch = ALBWProcedurePatch(player=self.player, player_name=self.player_name)
        patch.write_file("patch_info.bin", pickle.dumps(patch_info))

        # Write patch file
        out_file_name = self.multiworld.get_out_file_name_base(self.player)
        patch.write(os.path.join(output_directory, f"{out_file_name}{patch.patch_file_ending}"))
    
    def _initial_fill(self, itempool: List[Item], location_names: List[str]) -> None:
        for item in itempool:
            self.pre_fill_items.remove(item)
        state = CollectionState(self.multiworld)
        for item in self.pre_fill_items:
            state.collect(item)
        state = sweep_from_pool(state, self.itempool)
        locations = [loc for loc in self.multiworld.get_unfilled_locations(self.player) if loc.name in location_names]
        self.random.shuffle(locations)
        fill_restrictive(self.multiworld, state, locations, itempool,
            single_player_placement=True, lock=True, allow_excluded=True, allow_partial=False)

    def _convert_state(self, state: CollectionState) -> List[PyRandomizable]:
        randomizables = []
        for (name, count) in state.prog_items[self.player].items():
            item = item_table[name]
            randomizables.extend(item.progress[:count])
        return randomizables
    
    def _build_check_map(self) -> Dict[str, str]:
        # Replace all non-local items with Letter in a Bottle
        check_map = {loc.name: loc.item.name if loc.item.player == self.player
            else "AP Item" for loc in self.multiworld.get_locations(self.player)}
        
        # Fill in unrandomized Maiamai
        if not self.options.maiamai_mayhem:
            for loc in all_locations:
                if loc.loctype == LocationType.Maiamai:
                    check_map[loc.name] = Items.Maiamai.name
        
        # Fill in unrandomized upgrades
        if self.options.nice_items == NiceItems.option_vanilla:
            for loc in all_locations:
                if loc.loctype == LocationType.Upgrade:
                    assert loc.default_item is not None
                    check_map[loc.name] = loc.default_item.name
        else:
            for loc in all_locations:
                if loc.loctype == LocationType.Upgrade:
                    check_map[loc.name] = Items.RupeeGreen.name
        
        # Fill in inaccessible shop items
        check_map["Thieves' Town Item Shop (2)"] = Items.GoldBee.name
        check_map["Lorule Lakeside Item Shop (2)"] = Items.GoldBee.name

        return check_map

    def _get_item_count(self, item: ItemData):
        if item.itemtype == ItemType.Prize and self.options.randomize_dungeon_prizes:
            return 1
        if item.is_event():
            return 0
        if item.itemtype == ItemType.Junk:
            return 0
        if item == Items.Maiamai and not self.options.maiamai_mayhem:
            return 0
        if item.itemtype == ItemType.SmallKey and self.options.keysy in [Keysy.option_small, Keysy.option_all]:
            return 0
        if item.itemtype == ItemType.BigKey and self.options.keysy in [Keysy.option_big, Keysy.option_all]:
            return 0
        if item == Items.Quake and self.options.initial_crack_state == InitialCrackState.option_open:
            return 0
        if (item == Items.Lamp or item == Items.Net) and not self.options.super_items:
            return 1
        if item.itemtype == ItemType.Ravio and self.options.nice_items != NiceItems.option_shuffled:
            return 1
        if item == Items.BeeBadge and self.options.logic_mode == LogicMode.option_hell:
            return 0
        if item == Items.Sword and self.options.swordless_mode:
            return 0
        return item.count
    
    def _get_location_item(self, location: LocationData) -> Optional[ItemData]:
        # if location.loctype == LocationType.Upgrade and self.options.nice_mode:
        #     return None
        if location.loctype == LocationType.Prize and self.options.randomize_dungeon_prizes:
            return None
        if location.loctype == LocationType.Vane:
            assert self.seed_info is not None
            assert location.default_item is not None and location.default_item.vane is not None
            return vane_to_item[self.seed_info.vane_map[location.default_item.vane]]
        return location.default_item
    
    def _is_unrandomized(self, location: LocationData) -> bool:
        return (location.loctype == LocationType.Maiamai and not self.options.maiamai_mayhem) \
            or location.loctype == LocationType.Upgrade
            # or (location.loctype == LocationType.Upgrade and not self.options.nice_mode)
    
    def _save_for_pre_fill(self, item: ItemData) -> bool:
        return item.is_dungeon_item() \
            or (item.itemtype == ItemType.Prize and bool(self.options.randomize_dungeon_prizes)) \
            or (item == Items.BowOfLight and bool(self.options.bow_of_light_in_castle))
    
    def _get_random_weapon(self) -> ItemData:
        weapons = [Items.Bow, Items.Bombs, Items.FireRod, Items.IceRod, Items.Hammer, Items.Boots]
        if not self.options.swordless_mode:
            weapons.append(Items.Sword)
        if self.options.logic_mode != LogicMode.option_normal:
            weapons.extend([Items.Lamp, Items.Net])
        return self.random.choice(weapons)
