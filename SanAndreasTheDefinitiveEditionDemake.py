# Text-Based San Andreas - The Definitive Edition Demake
# Version: 2.0
# -----------------------------------------------
# 🆕 CHANGELOG:
# - ✅ Version 2.0: Major overhaul for "Definitive Edition"
# - ✅ Expanded Player Stats: Health, Money, Stamina, Driving, Weapon Skill
# - ✅ Hunger/Thirst System: Player needs to eat/drink
# - ✅ Wanted Level System: Police react to player crimes
# - ✅ Vehicles: Player can enter/exit, drive, and vehicles have health
# - ✅ Multiple Gangs/Factions: Basic reputation system
# - ✅ Enhanced Map: Zones/Districts with different characteristics
# - ✅ More Diverse Items: Food, Drinks, different Weapon types
# - ✅ Shops Categorization: Ammu-Nation, Cluckin' Bell, General Store
# - ✅ Mission System Improvements: More objective types
# - ✅ Dynamic World Events: Random police patrols, gang activity
# - ✅ Improved UI: Detailed status display, context-sensitive prompts
# - ✅ Robust Save/Load: Handles new game elements
# - ✅ Renamed "attack" to "f" for consistency
# - ✅ Fixed Big Smoke mission logic: now checks for Cash Bundle correctly
# - ✅ Added debug print to show player inventory in Big Smoke mission (useful for debugging)
# - ✅ Improved mission flow: Sweet ➜ Ryder ➜ Big Smoke
# - ✅ Added colors with colorama for clearer UI
# - ✅ Big Smoke occupies two tiles and is labeled as "BS" on the map
# - ✅ Enemy AI improved slightly (random movement + simple f)
# - ✅ Game supports save/load system with inventory + health + money
# ---
# 🔄 Version 2.0.1 Changes:
# - Changed save hotkey from 's' to 'v' to prevent conflicts with 's' (move down).
# ---
# 🔄 Version 2.0.2 Changes:
# - Implemented backward compatibility for save files:
#   - Save files now include a version number.
#   - `from_dict` methods for `Character`, `Player`, `BigSmoke`, `Enemy`, `Item` (and subclasses), `Shop`, and `Vehicle` now use `.get()` with default values for attributes introduced in later versions, preventing load errors from older saves.
# -----------------------------------------------

import time
import os
import random
import json
from colorama import init, Fore, Style

# Initialize Colorama for cross-platform colored output
init(autoreset=True)

# --- Constants ---
MAP_WIDTH = 80  # Increased map size for more exploration
MAP_HEIGHT = 25
PLAYER_CHAR = Fore.CYAN + 'C' + Style.RESET_ALL
NPC_CHAR = Fore.BLUE + 'N' + Style.RESET_ALL
BIG_SMOKE_CHARS = [Fore.MAGENTA + 'B' + Style.RESET_ALL, Fore.MAGENTA + 'S' + Style.RESET_ALL] # Big Smoke occupies two tiles
ITEM_CHAR = Fore.YELLOW + 'I' + Style.RESET_ALL
SHOP_CHAR = Fore.GREEN + 'S' + Style.RESET_ALL
ENEMY_CHAR = Fore.RED + 'E' + Style.RESET_ALL
VEHICLE_CHAR = Fore.WHITE + 'V' + Style.RESET_ALL
POLICE_CHAR = Fore.BLUE + 'P' + Style.RESET_ALL
EMPTY_CHAR = '.'
FOG_CHAR = ' ' # Character for unexplored areas in fog of war
GAME_TICK_RATE = 0.15 # How often the game updates (in seconds), slightly faster
VISION_RADIUS = 8 # How far the player can see, increased for larger map
MAX_WANTED_LEVEL = 5

# --- Utility Functions ---
def clear_console():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def clamp(value, min_value, max_value):
    """Clamps a value between a minimum and maximum."""
    return max(min_value, min(value, max_value))

# --- Base Classes ---

class GameObject:
    """Base class for all objects in the game world."""
    def __init__(self, x, y, char, name="Object"):
        self.x = x
        self.y = y
        self.char = char
        self.name = name

    def get_position(self):
        """Returns the current (x, y) position of the object."""
        return (self.x, self.y)

    def set_position(self, x, y):
        """Sets the position of the object."""
        self.x = x
        self.y = y

    def to_dict(self):
        """Converts the object's state to a dictionary for saving."""
        return {
            "x": self.x,
            "y": self.y,
            "char": self.char,
            "name": self.name,
            "type": self.__class__.__name__
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstructs an object from a dictionary."""
        # This will be overridden by subclasses for specific attributes
        return cls(data["x"], data["y"], data["char"], data["name"])

    def __repr__(self):
        """String representation for debugging."""
        return f"{self.name}({self.x}, {self.y})"

class Character(GameObject):
    """Base class for characters with health, inventory, and basic stats."""
    def __init__(self, x, y, char, name, health, money=0, stamina=100):
        super().__init__(x, y, char, name)
        self.health = health
        self.max_health = health # Store max health for healing
        self.inventory = []
        self.money = money
        self.stamina = stamina
        self.max_stamina = stamina
        self.current_weapon = None # Reference to a Weapon object in inventory

    def take_damage(self, amount):
        """Reduces character health by the given amount."""
        self.health -= amount
        if self.health < 0:
            self.health = 0
        print(f"{self.name} took {amount} damage. Health: {self.health}/{self.max_health}")
        return self.health == 0 # Return True if defeated

    def heal(self, amount):
        """Increases character health by the given amount, up to max health."""
        self.health += amount
        self.health = clamp(self.health, 0, self.max_health)
        print(f"{self.name} healed {amount} health. Health: {self.health}/{self.max_health}")

    def add_item(self, item):
        """Adds an item to the character's inventory."""
        self.inventory.append(item)
        print(f"{self.name} picked up {item.name}.")

    def remove_item(self, item):
        """Removes an item from the character's inventory."""
        if item in self.inventory:
            self.inventory.remove(item)
            # If the removed item was the current weapon, unequip it
            if self.current_weapon == item:
                self.current_weapon = None
            print(f"{self.name} used/removed {item.name}.")
            return True
        return False

    def equip_weapon(self, weapon):
        """Equips a weapon from the inventory."""
        if weapon in self.inventory and isinstance(weapon, Weapon):
            self.current_weapon = weapon
            print(f"{self.name} equipped {weapon.name}.")
        else:
            print(f"{weapon.name} is not in {self.name}'s inventory or is not a weapon.")

    def f(self, target):
        """Attacks a target using the current weapon or fists."""
        damage = 5 # Default fist damage
        weapon_name = "fists"
        if self.current_weapon:
            damage = self.current_weapon.damage
            weapon_name = self.current_weapon.name
        
        print(f"{self.name} attacks {target.name} with {weapon_name} for {damage} damage!")
        if target.take_damage(damage):
            print(f"{Fore.GREEN}{target.name} has been defeated!{Style.RESET_ALL}")
            return True # Target defeated
        return False # Target not defeated

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "health": self.health,
            "max_health": self.max_health,
            "money": self.money,
            "stamina": self.stamina,
            "max_stamina": self.max_stamina,
            "inventory": [item.to_dict() for item in self.inventory],
            "current_weapon": self.current_weapon.name if self.current_weapon else None
        })
        return data

    @classmethod
    def from_dict(cls, data):
        # Base Character reconstruction, handling new 'stamina' attribute with .get()
        obj = cls(
            data["x"],
            data["y"],
            data["char"],
            data["name"],
            data["health"],
            data.get("money", 0), # Default to 0 if money not in old save
            data.get("stamina", 100) # Default stamina for older saves
        )
        obj.max_health = data.get("max_health", data["health"]) # Default max_health
        obj.max_stamina = data.get("max_stamina", obj.stamina) # Default max_stamina
        obj.inventory = [ItemFactory.create_item_from_dict(item_data) for item_data in data.get("inventory", [])]
        if data.get("current_weapon"):
            for item in obj.inventory:
                if isinstance(item, Weapon) and item.name == data["current_weapon"]:
                    obj.current_weapon = item
                    break
        return obj

class Player(Character):
    """The player character."""
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_CHAR, "CJ", 100, money=500, stamina=100)
        self.discovered_map = [[False for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        self.missions_completed = []
        self.current_mission = None # Stores a Mission object
        self.wanted_level = 0
        self.hunger = 100 # 0 = starving, 100 = full
        self.thirst = 100 # 0 = dehydrated, 100 = hydrated
        self.driving_skill = 1
        self.weapon_skill = 1
        self.current_vehicle = None # Reference to a Vehicle object

    def discover_area(self, game_map):
        """Marks areas within vision radius as discovered."""
        for dy in range(-VISION_RADIUS, VISION_RADIUS + 1):
            for dx in range(-VISION_RADIUS, VISION_RADIUS + 1):
                nx, ny = self.x + dx, self.y + dy
                if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                    # Check if within a circular radius for a more natural fog
                    if (dx*dx + dy*dy) <= (VISION_RADIUS*VISION_RADIUS):
                        self.discovered_map[ny][nx] = True

    def move(self, dx, dy, game_map):
        """Moves the player by (dx, dy) if the new position is valid."""
        new_x, new_y = self.x + dx, self.y + dy

        if self.current_vehicle:
            return self.current_vehicle.move(dx, dy, game_map, self) # Vehicle handles movement logic
        else:
            # Check map boundaries
            if not (0 <= new_x < MAP_WIDTH and 0 <= new_y < MAP_HEIGHT):
                print(f"{Fore.RED}You hit the map boundary!{Style.RESET_ALL}")
                return False

            # Check for collisions with other objects (NPCs, Big Smoke, Enemies, Shops, Vehicles)
            for obj in game_map.get_all_objects():
                if obj != self and obj != self.current_vehicle: # Don't collide with self or current vehicle
                    # Handle Big Smoke occupying two tiles
                    if isinstance(obj, BigSmoke):
                        if (new_x == obj.x and new_y == obj.y) or \
                           (new_x == obj.x + 1 and new_y == obj.y): # Big Smoke's second tile
                            print(f"{Fore.YELLOW}You can't move there, {obj.name} is in the way!{Style.RESET_ALL}")
                            return False
                    elif new_x == obj.x and new_y == obj.y:
                        print(f"{Fore.YELLOW}You can't move there, {obj.name} is in the way!{Style.RESET_ALL}")
                        return False
            
            self.x = new_x
            self.y = new_y
            self.stamina = clamp(self.stamina - 1, 0, self.max_stamina) # Walking costs stamina
            return True

    def update_needs(self):
        """Decreases hunger and thirst over time."""
        self.hunger = clamp(self.hunger - 1, 0, 100)
        self.thirst = clamp(self.thirst - 1, 0, 100)

        if self.hunger <= 0 or self.thirst <= 0:
            self.take_damage(2) # Take damage if starving/dehydrated
            if self.hunger <= 0: print(f"{Fore.RED}You are starving! Find some food.{Style.RESET_ALL}")
            if self.thirst <= 0: print(f"{Fore.RED}You are dehydrated! Find some water.{Style.RESET_ALL}")

    def add_wanted_level(self, amount):
        """Increases wanted level."""
        self.wanted_level = clamp(self.wanted_level + amount, 0, MAX_WANTED_LEVEL)
        print(f"{Fore.RED}WANTED LEVEL: {self.wanted_level} STAR{'S' if self.wanted_level != 1 else ''}!{Style.RESET_ALL}")

    def reduce_wanted_level(self, amount):
        """Reduces wanted level."""
        self.wanted_level = clamp(self.wanted_level - amount, 0, MAX_WANTED_LEVEL)
        if self.wanted_level == 0:
            print(f"{Fore.GREEN}Wanted level cleared!{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Wanted level reduced to {self.wanted_level} star{'s' if self.wanted_level != 1 else ''}.{Style.RESET_ALL}")

    def display_status(self):
        """Prints the player's current status."""
        weapon_name = self.current_weapon.name if self.current_weapon else "None"
        vehicle_name = self.current_vehicle.name if self.current_vehicle else "None"
        print(f"\n--- {Fore.CYAN}CJ's Status{Style.RESET_ALL} ---")
        print(f"Health: {Fore.GREEN}{self.health}/{self.max_health}{Style.RESET_ALL} | Stamina: {Fore.YELLOW}{self.stamina}/{self.max_stamina}{Style.RESET_ALL}")
        print(f"Money: {Fore.YELLOW}${self.money}{Style.RESET_ALL} | Wanted: {Fore.RED}{'*' * self.wanted_level}{Style.RESET_ALL}")
        print(f"Hunger: {Fore.MAGENTA}{self.hunger}%{Style.RESET_ALL} | Thirst: {Fore.BLUE}{self.thirst}%{Style.RESET_ALL}")
        print(f"Weapon: {Fore.MAGENTA}{weapon_name}{Style.RESET_ALL} | Vehicle: {Fore.WHITE}{vehicle_name}{Style.RESET_ALL}")
        print(f"Inventory: {', '.join([item.name for item in self.inventory]) if self.inventory else 'Empty'}")
        print(f"Current Mission: {self.current_mission.name if self.current_mission else 'None'}")
        print(f"Missions Completed: {', '.join(self.missions_completed) if self.missions_completed else 'None'}")
        print("--------------------")

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "discovered_map": self.discovered_map,
            "missions_completed": self.missions_completed,
            "current_mission": self.current_mission.name if self.current_mission else None,
            "wanted_level": self.wanted_level,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "driving_skill": self.driving_skill,
            "weapon_skill": self.weapon_skill,
            "current_vehicle": self.current_vehicle.name if self.current_vehicle else None # Store vehicle name
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = super().from_dict(data) # Use Character's from_dict
        obj.discovered_map = data.get("discovered_map", [[False for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)])
        obj.missions_completed = data.get("missions_completed", [])
        obj.wanted_level = data.get("wanted_level", 0)
        obj.hunger = data.get("hunger", 100)
        obj.thirst = data.get("thirst", 100)
        obj.driving_skill = data.get("driving_skill", 1)
        obj.weapon_skill = data.get("weapon_skill", 1)
        obj.current_vehicle = None # Will be set by Game.load_game
        obj.current_mission = None # Will be set by Game.load_game

        # Ensure char is correctly colored after loading
        obj.char = PLAYER_CHAR
        return obj

class NPC(Character):
    """Non-Player Character."""
    def __init__(self, x, y, name, dialogue, char=NPC_CHAR):
        super().__init__(x, y, char, name, health=50)
        self.dialogue = dialogue
        self.mission_offered = None
        self.mission_completed = False

    def talk(self, player):
        """Initiates dialogue with the player and offers/completes missions."""
        print(f"{Fore.BLUE}{self.name}:{Style.RESET_ALL} {self.dialogue}")
        if self.mission_offered and not self.mission_completed:
            if self.mission_offered.is_completed(player):
                print(f"{Fore.GREEN}Mission '{self.mission_offered.name}' completed!{Style.RESET_ALL}")
                self.mission_offered.complete(player)
                player.missions_completed.append(self.mission_offered.name)
                player.current_mission = None
                self.mission_completed = True # Mark NPC's mission as completed
            elif not player.current_mission:
                print(f"{Fore.YELLOW}Do you want to accept mission '{self.mission_offered.name}'? (yes/no){Style.RESET_ALL}")
                choice = input("> ").lower()
                if choice == 'yes':
                    player.current_mission = self.mission_offered
                    print(f"{Fore.GREEN}Mission '{self.mission_offered.name}' accepted!{Style.RESET_ALL}")
                    print(f"Objective: {self.mission_offered.description}")
                else:
                    print(f"{Fore.RED}Mission declined.{Style.RESET_ALL}")
            elif player.current_mission == self.mission_offered:
                print(f"{Fore.YELLOW}You are currently on this mission. Objective: {self.mission_offered.description}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}You already have an active mission: {player.current_mission.name}. Complete it first!{Style.RESET_ALL}")

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "dialogue": self.dialogue,
            "mission_offered": self.mission_offered.name if self.mission_offered else None,
            "mission_completed": self.mission_completed
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = super().from_dict(data) # Use Character's from_dict
        obj.dialogue = data.get("dialogue", "...") # Default dialogue
        obj.mission_completed = data.get("mission_completed", False)
        obj.mission_offered = None # Will be set by Game.load_game
        return obj

class BigSmoke(NPC):
    """Special NPC: Big Smoke, occupies two tiles."""
    def __init__(self, x, y):
        # Big Smoke's primary position is (x,y), second tile is (x+1, y)
        super().__init__(x, y, "Big Smoke", "You picked the wrong house, fool!", char=BIG_SMOKE_CHARS[0])
        self.char2_x = x + 1
        self.char2_y = y

    def get_position(self):
        """Returns the primary position."""
        return (self.x, self.y)

    def get_all_positions(self):
        """Returns both positions occupied by Big Smoke."""
        return [(self.x, self.y), (self.char2_x, self.char2_y)]

    def talk(self, player):
        """Big Smoke's special dialogue and mission logic."""
        print(f"{Fore.BLUE}{self.name}:{Style.RESET_ALL} {self.dialogue}")
        print(f"[DEBUG] Inventory: {[item.name for item in player.inventory]}") # Debug print as requested

        if "Sweet's Mission" in player.missions_completed and "Ryder's Mission" in player.missions_completed:
            if not self.mission_completed:
                # Check if player has the Cash Bundle
                has_cash_bundle = any(isinstance(item, MoneyBundle) and item.name == "Cash Bundle" for item in player.inventory)

                if has_cash_bundle:
                    print(f"{Fore.BLUE}{self.name}:{Style.RESET_ALL} Ah, you got the cash! My man!")
                    if self.mission_offered and not self.mission_completed:
                        if self.mission_offered.is_completed(player):
                            print(f"{Fore.GREEN}Mission '{self.mission_offered.name}' completed!{Style.RESET_ALL}")
                            self.mission_offered.complete(player)
                            player.missions_completed.append(self.mission_offered.name)
                            player.current_mission = None
                            self.mission_completed = True # Mark Big Smoke's mission as completed
                else:
                    print(f"{Fore.BLUE}{self.name}:{Style.RESET_ALL} You need to find that cash bundle, CJ! It's somewhere out there.")
                    if not player.current_mission:
                        print(f"{Fore.YELLOW}Do you want to accept mission '{self.mission_offered.name}'? (yes/no){Style.RESET_ALL}")
                        choice = input("> ").lower()
                        if choice == 'yes':
                            player.current_mission = self.mission_offered
                            print(f"{Fore.GREEN}Mission '{self.mission_offered.name}' accepted!{Style.RESET_ALL}")
                            print(f"Objective: {self.mission_offered.description}")
                        else:
                            print(f"{Fore.RED}Mission declined.{Style.RESET_ALL}")
                    elif player.current_mission == self.mission_offered:
                        print(f"{Fore.YELLOW}You are currently on this mission. Objective: {self.mission_offered.description}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}You already have an active mission: {player.current_mission.name}. Complete it first!{Style.RESET_ALL}")
            else:
                print(f"{Fore.BLUE}{self.name}:{Style.RESET_ALL} All right, CJ, you're doing good. Now let's get some food!")
        else:
            print(f"{Fore.BLUE}{self.name}:{Style.RESET_ALL} Go see Sweet and Ryder first, CJ. They got somethin' for ya.")

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "char2_x": self.char2_x,
            "char2_y": self.char2_y
        })
        return data

    @classmethod
    def from_dict(cls, data):
        # BigSmoke specific reconstruction, handling new 'stamina' attribute with .get()
        obj = cls(data["x"], data["y"])
        obj.health = data.get("health", 50)
        obj.max_health = data.get("max_health", obj.health)
        obj.money = data.get("money", 0)
        obj.stamina = data.get("stamina", 100)
        obj.max_stamina = data.get("max_stamina", obj.stamina)
        obj.inventory = [ItemFactory.create_item_from_dict(item_data) for item_data in data.get("inventory", [])]
        obj.current_weapon = None # Big Smoke doesn't typically have a weapon in inventory
        obj.dialogue = data.get("dialogue", "You picked the wrong house, fool!")
        obj.mission_completed = data.get("mission_completed", False)
        obj.mission_offered = None # Will be set by Game.load_game
        return obj

class Enemy(Character):
    """An enemy character that can f the player."""
    def __init__(self, x, y, name, health, damage, faction="Gang"):
        super().__init__(x, y, ENEMY_CHAR, name, health)
        self.damage = damage
        self.faction = faction # e.g., "Ballaz", "Vagos", "Police"

    def move_randomly(self, game_map):
        """Moves the enemy randomly to an adjacent tile if possible."""
        possible_moves = [(0, 1), (0, -1), (1, 0), (-1, 0)] # Up, Down, Right, Left
        random.shuffle(possible_moves)

        for dx, dy in possible_moves:
            new_x, new_y = self.x + dx, self.y + dy
            if 0 <= new_x < MAP_WIDTH and 0 <= new_y < MAP_HEIGHT:
                # Check if the new position is empty (not occupied by player or other enemies/NPCs)
                is_occupied = False
                for obj in game_map.get_all_objects():
                    if obj != self and obj.x == new_x and obj.y == new_y:
                        is_occupied = True
                        break
                if not is_occupied:
                    self.x = new_x
                    self.y = new_y
                    return True
        return False # Could not move

    def take_turn(self, player, game_map):
        """Enemy's turn: move towards player or f if close."""
        if self.health <= 0: return # Dead enemies don't take turns

        # Police specific behavior: prioritize pursuit if player has wanted level
        if self.faction == "Police" and player.wanted_level > 0:
            # Simple pursuit: move directly towards player
            dx = 0
            if player.x > self.x: dx = 1
            elif player.x < self.x: dx = -1

            dy = 0
            if player.y > self.y: dy = 1
            elif player.y < self.y: dy = -1

            # Try to move towards player, if blocked, try random move
            if (dx != 0 or dy != 0) and self.move_towards(player.x, player.y, game_map):
                pass # Successfully moved towards player
            else:
                self.move_randomly(game_map) # Fallback to random if direct path blocked

        else: # General enemy behavior
            # Check if player is adjacent
            if abs(self.x - player.x) <= 1 and abs(self.y - player.y) <= 1:
                self.f(player)
            else:
                self.move_randomly(game_map) # Simple random movement

    def move_towards(self, target_x, target_y, game_map):
        """Attempts to move the enemy one step closer to target (x,y)."""
        dx, dy = 0, 0
        if target_x > self.x: dx = 1
        elif target_x < self.x: dx = -1

        if target_y > self.y: dy = 1
        elif target_y < self.y: dy = -1

        new_x, new_y = self.x + dx, self.y + dy

        if 0 <= new_x < MAP_WIDTH and 0 <= new_y < MAP_HEIGHT:
            is_occupied = False
            for obj in game_map.get_all_objects():
                if obj != self and obj.x == new_x and obj.y == new_y:
                    is_occupied = True
                    break
            if not is_occupied:
                self.x = new_x
                self.y = new_y
                return True
        return False

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "damage": self.damage,
            "faction": self.faction
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("health", 40), # Default health
            data.get("damage", 10), # Default damage
            data.get("faction", "Gang") # Default faction for older saves
        )
        obj.max_health = data.get("max_health", obj.health)
        obj.money = data.get("money", 0)
        obj.stamina = data.get("stamina", 100)
        obj.max_stamina = data.get("max_stamina", obj.stamina)
        obj.inventory = [ItemFactory.create_item_from_dict(item_data) for item_data in data.get("inventory", [])]
        obj.current_weapon = None # Enemies don't typically have equipped weapons in inventory
        # Ensure char is correctly colored after loading
        obj.char = ENEMY_CHAR if obj.faction != "Police" else POLICE_CHAR
        return obj

class Item(GameObject):
    """Base class for items that can be picked up."""
    def __init__(self, x, y, name, description, char=ITEM_CHAR, value=0):
        super().__init__(x, y, char, name)
        self.description = description
        self.value = value # Monetary value

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "description": self.description,
            "value": self.value
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("description", "A generic item."),
            char=data.get("char", ITEM_CHAR),
            value=data.get("value", 0) # Default value for older saves
        )
        return obj

class Weapon(Item):
    """A weapon item with a damage value."""
    def __init__(self, x, y, name, description, damage, value):
        super().__init__(x, y, name, description, value=value)
        self.damage = damage

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "damage": self.damage
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("description", "A weapon."),
            data.get("damage", 1), # Default damage
            data.get("value", 0) # Default value
        )
        obj.char = data.get("char", ITEM_CHAR) # Ensure char is set
        return obj

class HealthPack(Item):
    """A health pack item that restores health."""
    def __init__(self, x, y, name, description, heal_amount, value):
        super().__init__(x, y, name, description, value=value)
        self.heal_amount = heal_amount

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "heal_amount": self.heal_amount
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("description", "A health pack."),
            data.get("heal_amount", 25), # Default heal amount
            data.get("value", 0) # Default value
        )
        obj.char = data.get("char", ITEM_CHAR) # Ensure char is set
        return obj

class MoneyBundle(Item):
    """A bundle of money."""
    def __init__(self, x, y, name, description, amount):
        super().__init__(x, y, name, description, value=amount) # Value is the amount
        self.amount = amount

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "amount": self.amount
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("description", "A bundle of cash."),
            data.get("amount", 0) # Default amount
        )
        obj.char = data.get("char", ITEM_CHAR) # Ensure char is set
        return obj

class Food(Item):
    """Food item that restores hunger."""
    def __init__(self, x, y, name, description, hunger_restore, value):
        super().__init__(x, y, name, description, value=value)
        self.hunger_restore = hunger_restore

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "hunger_restore": self.hunger_restore
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("description", "Some food."),
            data.get("hunger_restore", 20), # Default hunger restore
            data.get("value", 0) # Default value
        )
        obj.char = data.get("char", ITEM_CHAR) # Ensure char is set
        return obj

class Drink(Item):
    """Drink item that restores thirst."""
    def __init__(self, x, y, name, description, thirst_restore, value):
        super().__init__(x, y, name, description, value=value)
        self.thirst_restore = thirst_restore

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "thirst_restore": self.thirst_restore
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("description", "A drink."),
            data.get("thirst_restore", 20), # Default thirst restore
            data.get("value", 0) # Default value
        )
        obj.char = data.get("char", ITEM_CHAR) # Ensure char is set
        return obj

class ItemFactory:
    """A factory to create item objects from dictionary data."""
    @staticmethod
    def create_item_from_dict(data):
        item_type = data.get("type", "Item") # Default to Item if type not specified
        if item_type == "Weapon":
            return Weapon.from_dict(data)
        elif item_type == "HealthPack":
            return HealthPack.from_dict(data)
        elif item_type == "MoneyBundle":
            return MoneyBundle.from_dict(data)
        elif item_type == "Food":
            return Food.from_dict(data)
        elif item_type == "Drink":
            return Drink.from_dict(data)
        else:
            return Item.from_dict(data)


class Shop(GameObject):
    """A shop where the player can buy items."""
    def __init__(self, x, y, name, inventory, shop_type="General"):
        super().__init__(x, y, SHOP_CHAR, name)
        self.inventory = inventory # List of (item_object, price) tuples
        self.shop_type = shop_type # e.g., "Ammu-Nation", "Cluckin' Bell", "General Store"

    def enter(self, player):
        """Allows the player to interact with the shop."""
        print(f"\n--- {Fore.GREEN}Welcome to {self.name} ({self.shop_type})!{Style.RESET_ALL} ---")
        print("Available items:")
        if not self.inventory:
            print("No items available.")
            print("0. Exit shop")
        else:
            for i, (item, price) in enumerate(self.inventory):
                print(f"{i+1}. {item.name} ({item.description}) - ${price}")
            print("0. Exit shop")

        while True:
            try:
                choice = input(f"Your money: ${player.money}. Enter item number to buy (0 to exit): ")
                if choice == '0':
                    print(f"{Fore.YELLOW}Exiting shop.{Style.RESET_ALL}")
                    break
                
                choice = int(choice)
                if 1 <= choice <= len(self.inventory):
                    item_to_buy, price = self.inventory[choice - 1]
                    if player.money >= price:
                        player.money -= price
                        player.add_item(item_to_buy)
                        print(f"{Fore.GREEN}You bought {item_to_buy.name} for ${price}. Remaining money: ${player.money}{Style.RESET_ALL}")
                        # Optionally, remove item from shop inventory after purchase if it's a limited stock item
                        # self.inventory.pop(choice - 1)
                    else:
                        print(f"{Fore.RED}Not enough money to buy {item_to_buy.name}.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid choice. Please enter a valid number.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a number.{Style.RESET_ALL}")

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "inventory": [(item.to_dict(), price) for item, price in self.inventory],
            "shop_type": self.shop_type
        })
        return data

    @classmethod
    def from_dict(cls, data):
        # Reconstruct shop inventory items, handling missing 'inventory' key
        inventory = [(ItemFactory.create_item_from_dict(item_data), price) for item_data, price in data.get("inventory", [])]
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            inventory,
            data.get("shop_type", "General") # Default shop_type for older saves
        )
        # Ensure char is correctly colored after loading
        obj.char = SHOP_CHAR
        return obj

class Vehicle(GameObject):
    """A vehicle that the player can enter and drive."""
    def __init__(self, x, y, name, health, speed, char=VEHICLE_CHAR):
        super().__init__(x, y, char, name)
        self.health = health
        self.max_health = health
        self.speed = speed # How many tiles it can move per turn (simplified)
        self.occupant = None # Reference to the Character currently in the vehicle

    def enter(self, character):
        """Allows a character to enter the vehicle."""
        if self.occupant is None:
            self.occupant = character
            character.current_vehicle = self
            print(f"{character.name} entered the {self.name}.")
            return True
        else:
            print(f"The {self.name} is already occupied by {self.occupant.name}.")
            return False

    def exit(self, character):
        """Allows a character to exit the vehicle."""
        if self.occupant == character:
            self.occupant = None
            character.current_vehicle = None
            # Place character next to the vehicle
            character.x = self.x + 1 # Try to place to the right
            character.y = self.y
            print(f"{character.name} exited the {self.name}.")
            return True
        else:
            print(f"{character.name} is not in this {self.name}.")
            return False

    def move(self, dx, dy, game_map, player):
        """Moves the vehicle (and its occupant) by (dx, dy)."""
        new_x, new_y = self.x + dx, self.y + dy

        # Check map boundaries
        if not (0 <= new_x < MAP_WIDTH and 0 <= new_y < MAP_HEIGHT):
            print(f"{Fore.RED}The {self.name} hit the map boundary!{Style.RESET_ALL}")
            return False

        # Check for collisions with other objects (excluding occupant)
        for obj in game_map.get_all_objects():
            if obj != self and obj != self.occupant:
                # Special handling for Big Smoke occupying two tiles
                if isinstance(obj, BigSmoke):
                    if (new_x == obj.x and new_y == obj.y) or \
                       (new_x == obj.x + 1 and new_y == obj.y):
                        print(f"{Fore.YELLOW}The {self.name} can't move there, {obj.name} is in the way!{Style.RESET_ALL}")
                        return False
                elif new_x == obj.x and new_y == obj.y:
                    print(f"{Fore.YELLOW}The {self.name} can't move there, {obj.name} is in the way!{Style.RESET_ALL}")
                    return False
        
        self.x = new_x
        self.y = new_y
        if self.occupant:
            self.occupant.x = new_x
            self.occupant.y = new_y
            player.stamina = clamp(player.stamina - 0.5, 0, player.max_stamina) # Driving costs less stamina
        return True

    def take_damage(self, amount):
        """Reduces vehicle health."""
        self.health -= amount
        if self.health < 0:
            self.health = 0
        print(f"The {self.name} took {amount} damage. Health: {self.health}/{self.max_health}")
        if self.health == 0:
            print(f"{Fore.RED}The {self.name} is destroyed!{Style.RESET_ALL}")
            return True # Vehicle destroyed
        return False

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "health": self.health,
            "max_health": self.max_health,
            "speed": self.speed,
            "occupant": self.occupant.name if self.occupant else None # Store occupant's name, not object
        })
        return data

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            data["x"],
            data["y"],
            data["name"],
            data.get("health", 100), # Default health
            data.get("speed", 1), # Default speed
            char=data.get("char", VEHICLE_CHAR)
        )
        obj.max_health = data.get("max_health", obj.health)
        obj.occupant = None # Will be set by Game.load_game
        # Ensure char is correctly colored after loading
        obj.char = VEHICLE_CHAR
        return obj

class Mission:
    """Represents a mission with objectives and rewards."""
    def __init__(self, name, description, objective_func, reward_money=0, reward_item=None, prerequisite_missions=None):
        self.name = name
        self.description = description
        self.objective_func = objective_func # A function that takes player and returns True if objective met
        self.reward_money = reward_money
        self.reward_item = reward_item
        self.prerequisite_missions = prerequisite_missions if prerequisite_missions is not None else []

    def is_completed(self, player):
        """Checks if the mission objective is met."""
        return self.objective_func(player)

    def complete(self, player):
        """Applies mission rewards to the player."""
        player.money += self.reward_money
        print(f"{Fore.GREEN}Received ${self.reward_money} as reward.{Style.RESET_ALL}")
        if self.reward_item:
            player.add_item(self.reward_item)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            # objective_func cannot be directly serialized, will be re-assigned on load
            "reward_money": self.reward_money,
            "reward_item": self.reward_item.to_dict() if self.reward_item else None,
            "prerequisite_missions": self.prerequisite_missions
        }

    @classmethod
    def from_dict(cls, data, objective_func_map):
        # objective_func_map is a dictionary mapping mission names to their objective functions
        reward_item = ItemFactory.create_item_from_dict(data["reward_item"]) if data.get("reward_item") else None
        obj = cls(
            name=data["name"],
            description=data["description"],
            objective_func=objective_func_map.get(data["name"]), # Get the function from the map
            reward_money=data.get("reward_money", 0),
            reward_item=reward_item,
            prerequisite_missions=data.get("prerequisite_missions", [])
        )
        return obj

# --- Game Map and Logic ---

class GameMap:
    """Manages the game world, including objects and rendering."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.objects = [] # List of all game objects
        self.zones = {} # Example: {"Grove Street": [(x1,y1), (x2,y2)], ...}

    def add_object(self, obj):
        """Adds a game object to the map."""
        self.objects.append(obj)

    def remove_object(self, obj):
        """Removes a game object from the map."""
        if obj in self.objects:
            self.objects.remove(obj)

    def get_object_at(self, x, y):
        """Returns the first object found at (x, y), or None."""
        for obj in self.objects:
            # Special handling for Big Smoke occupying two tiles
            if isinstance(obj, BigSmoke):
                if (obj.x == x and obj.y == y) or (obj.char2_x == x and obj.char2_y == y):
                    return obj
            elif obj.x == x and obj.y == y:
                return obj
        return None

    def get_all_objects(self):
        """Returns a list of all objects currently on the map."""
        return self.objects

    def render(self, player):
        """Renders the current state of the map to the console."""
        clear_console() # Clear console

        print(f"{Fore.WHITE}--- Text-Based San Andreas ---{Style.RESET_ALL}")
        print(f"Health: {Fore.GREEN}{player.health}/{player.max_health}{Style.RESET_ALL} | Stamina: {Fore.YELLOW}{player.stamina}/{player.max_stamina}{Style.RESET_ALL} | Money: {Fore.YELLOW}${player.money}{Style.RESET_ALL} | Wanted: {Fore.RED}{'*' * player.wanted_level}{Style.RESET_ALL}")
        print(f"Hunger: {Fore.MAGENTA}{player.hunger}%{Style.RESET_ALL} | Thirst: {Fore.BLUE}{player.thirst}%{Style.RESET_ALL} | Time: {Game.current_time_str()}{Style.RESET_ALL}")
        print(f"Mission: {player.current_mission.name if player.current_mission else 'None'}")
        print("-" * (self.width + 2))

        # Create an empty map grid
        grid = [[EMPTY_CHAR for _ in range(self.width)] for _ in range(self.height)]

        # Place objects on the grid
        for obj in self.objects:
            if isinstance(obj, BigSmoke):
                # Place Big Smoke's first char
                if 0 <= obj.y < self.height and 0 <= obj.x < self.width:
                    grid[obj.y][obj.x] = BIG_SMOKE_CHARS[0]
                # Place Big Smoke's second char
                if 0 <= obj.char2_y < self.height and 0 <= obj.char2_x < self.width:
                    grid[obj.char2_y][obj.char2_x] = BIG_SMOKE_CHARS[1]
            elif 0 <= obj.y < self.height and 0 <= obj.x < self.width:
                if isinstance(obj, Player):
                    # Player is rendered separately on top
                    pass
                elif isinstance(obj, NPC):
                    grid[obj.y][obj.x] = NPC_CHAR
                elif isinstance(obj, Item):
                    grid[obj.y][obj.x] = ITEM_CHAR
                elif isinstance(obj, Shop):
                    grid[obj.y][obj.x] = SHOP_CHAR
                elif isinstance(obj, Enemy):
                    grid[obj.y][obj.x] = ENEMY_CHAR if obj.faction != "Police" else POLICE_CHAR
                elif isinstance(obj, Vehicle) and obj.occupant is None: # Only show vehicles if empty
                    grid[obj.y][obj.x] = VEHICLE_CHAR
                else:
                    grid[obj.y][obj.x] = obj.char # Default color for other objects

        # Place player (or player's vehicle) on top
        if player.current_vehicle:
            grid[player.current_vehicle.y][player.current_vehicle.x] = VEHICLE_CHAR
        grid[player.y][player.x] = PLAYER_CHAR

        # Print the grid with fog of war
        for y in range(self.height):
            row_chars = []
            for x in range(self.width):
                if player.discovered_map[y][x]:
                    row_chars.append(grid[y][x])
                else:
                    row_chars.append(FOG_CHAR) # Undiscovered area
            print("".join(row_chars))
        print("-" * (self.width + 2))

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "objects": [obj.to_dict() for obj in self.objects if not isinstance(obj, Player)] # Player saved separately
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["width"], data["height"])
        # Objects will be loaded and added by Game.load_game
        return obj


class Game:
    """Main game class, manages game state, map, and interactions."""
    _instance = None # Singleton instance
    _SAVE_FILE_VERSION = 2 # Current save file version

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Game, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
        self.player = Player(MAP_WIDTH // 2, MAP_HEIGHT // 2) # Start player in the center
        self.game_map.add_object(self.player)
        self.running = True
        self.game_time = 0 # In game ticks

        self.npcs = {}
        self.items = {}
        self.shops = {}
        self.enemies = {}
        self.vehicles = {}
        self.missions = {} # Store all mission definitions

        self._initialize_game_objects()
        self._initialize_missions()
        self._initialized = True

    @staticmethod
    def current_time_str():
        """Returns the current game time as a formatted string."""
        game_instance = Game._instance
        if game_instance:
            hours = (game_instance.game_time // 100) % 24 # Roughly 100 ticks per hour
            minutes = (game_instance.game_time % 100) * 0.6 # Convert remaining ticks to minutes
            return f"{int(hours):02d}:{int(minutes):02d}"
        return "00:00"

    def _initialize_game_objects(self):
        """Initializes all NPCs, items, shops, enemies, and vehicles."""
        # NPCs
        sweet = NPC(5, 5, "Sweet", "Hey CJ, long time no see! We got some business to handle.")
        self.game_map.add_object(sweet)
        self.npcs["sweet"] = sweet

        ryder = NPC(10, 10, "Ryder", "Yo, CJ! You still busta? Go get me some spray cans.")
        self.game_map.add_object(ryder)
        self.npcs["ryder"] = ryder

        big_smoke = BigSmoke(20, 15) # Big Smoke occupies (20,15) and (21,15)
        self.game_map.add_object(big_smoke)
        self.npcs["big_smoke"] = big_smoke

        # Items (initial placement)
        pistol = Weapon(2, 2, "Pistol", "A basic handgun.", 15, 75)
        self.game_map.add_object(pistol)
        self.items["pistol"] = pistol

        shotgun = Weapon(MAP_WIDTH - 5, MAP_HEIGHT - 5, "Shotgun", "Deals heavy damage up close.", 30, 200)
        self.game_map.add_object(shotgun)
        self.items["shotgun"] = shotgun

        health_pack_1 = HealthPack(7, 7, "Small Health Pack", "Restores a bit of health.", 25, 30)
        self.game_map.add_object(health_pack_1)
        self.items["health_pack_1"] = health_pack_1

        cash_bundle = MoneyBundle(MAP_WIDTH // 4, MAP_HEIGHT // 4, "Cash Bundle", "A stack of money.", 200)
        self.game_map.add_object(cash_bundle)
        self.items["cash_bundle"] = cash_bundle

        # Shops
        ammu_nation_items = [
            (Weapon(0, 0, "Knife", "A sharp blade.", 10, 50), 50), # x,y are placeholders for shop items
            (Weapon(0, 0, "Uzi", "Fast firing submachine gun.", 20, 150), 150),
            (HealthPack(0, 0, "Large Health Pack", "Restores a lot of health.", 50, 75), 75)
        ]
        ammu_nation = Shop(MAP_WIDTH - 10, 5, "Ammu-Nation", ammu_nation_items, "Ammu-Nation")
        self.game_map.add_object(ammu_nation)
        self.shops["ammu_nation"] = ammu_nation

        cluckin_bell_items = [
            (Food(0,0,"Cluckin' Bell Burger", "A greasy burger.", 40, 15), 15),
            (Drink(0,0,"Sprunk", "Refreshing soda.", 30, 10), 10)
        ]
        cluckin_bell = Shop(MAP_WIDTH // 2, 2, "Cluckin' Bell", cluckin_bell_items, "Fast Food")
        self.game_map.add_object(cluckin_bell)
        self.shops["cluckin_bell"] = cluckin_bell

        # Enemies
        gangster1 = Enemy(15, 10, "Gangster", 40, 10, "Ballaz")
        self.game_map.add_object(gangster1)
        self.enemies["gangster1"] = gangster1

        gangster2 = Enemy(25, 8, "Gangster", 40, 10, "Vagos")
        self.game_map.add_object(gangster2)
        self.enemies["gangster2"] = gangster2

        police_officer = Enemy(MAP_WIDTH - 2, 2, "Police Officer", 60, 15, "Police")
        self.game_map.add_object(police_officer)
        self.enemies["police_officer"] = police_officer

        # Vehicles
        green_sabre = Vehicle(30, 10, "Green Sabre", 100, 3)
        self.game_map.add_object(green_sabre)
        self.vehicles["green_sabre"] = green_sabre

        police_car = Vehicle(MAP_WIDTH - 5, 15, "Police Car", 120, 4)
        self.game_map.add_object(police_car)
        self.vehicles["police_car"] = police_car


    def _initialize_missions(self):
        """Defines and assigns missions to NPCs."""
        # Objective functions (must be defined here or globally accessible)
        def sweet_objective(player):
            return any(isinstance(item, Weapon) and item.name == "Pistol" for item in player.inventory)

        def ryder_objective(player):
            return any(isinstance(item, Weapon) and item.name == "Shotgun" for item in player.inventory)

        def big_smoke_objective(player):
            return any(isinstance(item, MoneyBundle) and item.name == "Cash Bundle" for item in player.inventory)

        # Store objective functions in a map for loading
        self.objective_func_map = {
            "Sweet's Mission": sweet_objective,
            "Ryder's Mission": ryder_objective,
            "Big Smoke's Mission": big_smoke_objective
        }

        # Sweet's Mission: Find the Pistol
        sweet_mission = Mission(
            name="Sweet's Mission",
            description="Find the Pistol and bring it back to Sweet.",
            objective_func=sweet_objective,
            reward_money=100
        )
        self.npcs["sweet"].mission_offered = sweet_mission
        self.missions["Sweet's Mission"] = sweet_mission

        # Ryder's Mission: Acquire the Shotgun (from map, not shop)
        ryder_mission = Mission(
            name="Ryder's Mission",
            description="Find the Shotgun and show it to Ryder.",
            objective_func=ryder_objective,
            reward_money=150,
            prerequisite_missions=["Sweet's Mission"]
        )
        self.npcs["ryder"].mission_offered = ryder_mission
        self.missions["Ryder's Mission"] = ryder_mission

        # Big Smoke's Mission: Collect Cash Bundle
        big_smoke_mission = Mission(
            name="Big Smoke's Mission",
            description="Collect the Cash Bundle for Big Smoke.",
            objective_func=big_smoke_objective,
            reward_money=200,
            prerequisite_missions=["Sweet's Mission", "Ryder's Mission"]
        )
        self.npcs["big_smoke"].mission_offered = big_smoke_mission
        self.missions["Big Smoke's Mission"] = big_smoke_mission

    def save_game(self, filename="savegame.json"):
        """Saves the current game state to a JSON file."""
        data = {
            "version": self._SAVE_FILE_VERSION, # Add current save file version
            "game_time": self.game_time,
            "player": self.player.to_dict(),
            "npcs": {name: npc.to_dict() for name, npc in self.npcs.items()},
            "shops": {name: shop.to_dict() for name, shop in self.shops.items()},
            "enemies": {name: enemy.to_dict() for name, enemy in self.enemies.items()},
            "vehicles": {name: vehicle.to_dict() for name, vehicle in self.vehicles.items()},
            # Only save items that are *on the map* and not in player inventory
            "items_on_map": [item.to_dict() for item in self.game_map.get_all_objects() if isinstance(item, Item) and item not in self.player.inventory],
        }
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"{Fore.GREEN}Game saved successfully to {filename}!{Style.RESET_ALL}")
        except IOError as e:
            print(f"{Fore.RED}Error saving game: {e}{Style.RESET_ALL}")

    def load_game(self, filename="savegame.json"):
        """Loads game state from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            saved_version = data.get("version", 1) # Default to 1 if no version found (pre-2.0)

            # Reset game state
            self.game_map.objects = []
            self.npcs = {}
            self.items = {}
            self.shops = {}
            self.enemies = {}
            self.vehicles = {}
            self.player = None # Will be re-created

            self.game_time = data.get("game_time", 0) # Default game_time for older saves

            # Load Player
            self.player = Player.from_dict(data["player"])
            self.game_map.add_object(self.player)

            # Load NPCs
            for name, npc_data in data.get("npcs", {}).items():
                if npc_data.get("type") == "BigSmoke":
                    npc_obj = BigSmoke.from_dict(npc_data)
                else:
                    npc_obj = NPC.from_dict(npc_data)
                self.npcs[name] = npc_obj
                self.game_map.add_object(npc_obj)
                # Re-assign mission_offered
                if npc_data.get("mission_offered") and npc_data["mission_offered"] in self.missions:
                    npc_obj.mission_offered = self.missions[npc_data["mission_offered"]]

            # Load Shops
            for name, shop_data in data.get("shops", {}).items():
                shop_obj = Shop.from_dict(shop_data)
                self.shops[name] = shop_obj
                self.game_map.add_object(shop_obj)

            # Load Enemies
            for name, enemy_data in data.get("enemies", {}).items():
                enemy_obj = Enemy.from_dict(enemy_data)
                self.enemies[name] = enemy_obj
                self.game_map.add_object(enemy_obj)

            # Load Vehicles
            for name, vehicle_data in data.get("vehicles", {}).items():
                vehicle_obj = Vehicle.from_dict(vehicle_data)
                self.vehicles[name] = vehicle_obj
                self.game_map.add_object(vehicle_obj)
                # Re-assign vehicle occupant if player was in it
                if vehicle_data.get("occupant") == self.player.name:
                    vehicle_obj.occupant = self.player
                    self.player.current_vehicle = vehicle_obj


            # Load Items on Map
            for item_data in data.get("items_on_map", []):
                item_obj = ItemFactory.create_item_from_dict(item_data)
                self.game_map.add_object(item_obj)
                self.items[item_obj.name] = item_obj # Add to items dict if needed for lookup

            # Re-assign player's current mission
            if data["player"].get("current_mission") and data["player"]["current_mission"] in self.missions:
                self.player.current_mission = self.missions[data["player"]["current_mission"]]

            print(f"{Fore.GREEN}Game loaded successfully from {filename}! (Save version: {saved_version}){Style.RESET_ALL}")
        except FileNotFoundError:
            print(f"{Fore.RED}Save file '{filename}' not found. Starting new game.{Style.RESET_ALL}")
            self._initialized = False # Re-initialize if no save found
            self.__init__() # Call init again to set up a new game
        except json.JSONDecodeError:
            print(f"{Fore.RED}Error decoding save file. It might be corrupted. Starting new game.{Style.RESET_ALL}")
            self._initialized = False
            self.__init__()
        except Exception as e:
            print(f"{Fore.RED}An unexpected error occurred while loading game: {e}. Starting new game.{Style.RESET_ALL}")
            self._initialized = False
            self.__init__()

    def handle_input(self, key):
        """Processes player input."""
        player = self.player
        current_x, current_y = player.get_position()

        if key == 'e': # Interact / Enter Vehicle
            interacted = False
            # Check for objects in adjacent cells first for interaction
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx == 0 and dy == 0: continue # Skip player's own cell
                    target_x, target_y = current_x + dx, current_y + dy
                    obj = self.game_map.get_object_at(target_x, target_y)

                    if obj:
                        if isinstance(obj, NPC):
                            # Check mission prerequisites before talking to NPC
                            if obj.mission_offered:
                                all_prereqs_met = True
                                for prereq_name in obj.mission_offered.prerequisite_missions:
                                    if prereq_name not in player.missions_completed:
                                        print(f"{Fore.RED}You need to complete '{prereq_name}' first to talk to {obj.name}.{Style.RESET_ALL}")
                                        all_prereqs_met = False
                                        break
                                if all_prereqs_met:
                                    obj.talk(player)
                                    interacted = True
                                    break
                                else:
                                    # If prereqs not met, still allow basic talk if no mission is offered
                                    if not obj.mission_offered:
                                        obj.talk(player)
                                        interacted = True
                                        break
                            else: # NPC has no mission offered
                                obj.talk(player)
                                interacted = True
                                break
                        elif isinstance(obj, Item):
                            player.add_item(obj)
                            self.game_map.remove_object(obj) # Remove item from map after pickup
                            interacted = True
                            break
                        elif isinstance(obj, Shop):
                            obj.enter(player)
                            interacted = True
                            break
                        elif isinstance(obj, Vehicle) and player.current_vehicle is None:
                            if obj.enter(player):
                                interacted = True
                                break
                if interacted: break
            if not interacted:
                print(f"{Fore.YELLOW}Nothing to interact with nearby.{Style.RESET_ALL}")

        elif key == 'x': # Exit Vehicle
            if player.current_vehicle:
                player.current_vehicle.exit(player)
            else:
                print(f"{Fore.YELLOW}You are not in a vehicle.{Style.RESET_ALL}")

        elif key == 'u': # Use item from inventory (e.g., health pack, equip weapon, food, drink)
            if not player.inventory:
                print(f"{Fore.YELLOW}Your inventory is empty.{Style.RESET_ALL}")
                return

            print(f"{Fore.MAGENTA}Your Inventory:{Style.RESET_ALL}")
            for i, item in enumerate(player.inventory):
                print(f"{i+1}. {item.name} ({item.description})")
            print("0. Cancel")

            try:
                choice = input("Enter number of item to use/equip: ")
                if choice == '0':
                    print("Action cancelled.")
                    return
                
                choice = int(choice)
                if 1 <= choice <= len(player.inventory):
                    selected_item = player.inventory[choice - 1]
                    if isinstance(selected_item, HealthPack):
                        player.heal(selected_item.heal_amount)
                        player.remove_item(selected_item)
                    elif isinstance(selected_item, Weapon):
                        player.equip_weapon(selected_item)
                    elif isinstance(selected_item, Food):
                        player.hunger = clamp(player.hunger + selected_item.hunger_restore, 0, 100)
                        print(f"{Fore.GREEN}You ate {selected_item.name}. Hunger: {player.hunger}%{Style.RESET_ALL}")
                        player.remove_item(selected_item)
                    elif isinstance(selected_item, Drink):
                        player.thirst = clamp(player.thirst + selected_item.thirst_restore, 0, 100)
                        print(f"{Fore.GREEN}You drank {selected_item.name}. Thirst: {player.thirst}%{Style.RESET_ALL}")
                        player.remove_item(selected_item)
                    else:
                        print(f"{Fore.YELLOW}You can't use {selected_item.name} this way.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a number.{Style.RESET_ALL}")

        elif key == 'f': # F (Attack)
            target_enemy = None
            # Look for an adjacent enemy to attack
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx == 0 and dy == 0: continue
                    obj = self.game_map.get_object_at(player.x + dx, player.y + dy)
                    if isinstance(obj, Enemy):
                        target_enemy = obj
                        break
                if target_enemy: break

            if target_enemy:
                if player.f(target_enemy): # If target defeated
                    self.game_map.remove_object(target_enemy)
                    # Remove from enemies dictionary
                    for name, enemy_obj in list(self.enemies.items()):
                        if enemy_obj == target_enemy:
                            del self.enemies[name]
                            break
                    # Increase wanted level if attacking police
                    if target_enemy.faction == "Police":
                        player.add_wanted_level(2) # Higher wanted level for attacking police
                    else:
                        player.add_wanted_level(1) # General crime
            else:
                print(f"{Fore.YELLOW}No enemies nearby to f.{Style.RESET_ALL}")

        elif key == 'v': # Save game (changed from 's')
            self.save_game()
        elif key == 'l': # Load game
            self.load_game()
        elif key == 'q': # Quit game
            print(f"{Fore.YELLOW}Quitting game. Goodbye!{Style.RESET_ALL}")
            self.running = False
            return
        elif key in ['w', 'a', 's', 'd']: # Movement
            dx, dy = 0, 0
            if key == 'w': dy = -1
            elif key == 's': dy = 1
            elif key == 'a': dx = -1
            elif key == 'd': dx = 1
            player.move(dx, dy, self.game_map)
        else:
            print(f"{Fore.RED}Invalid input. Use W/A/S/D - move, E - interact/enter vehicle, X - exit vehicle, U - use item, F - attack, V - save, L - load, Q - quit.{Style.RESET_ALL}")

        # After any action, update discovered map
        player.discover_area(self.game_map)

    def spawn_police(self):
        """Spawns police officers if wanted level is high."""
        if self.player.wanted_level > 0:
            num_police_to_spawn = self.player.wanted_level
            for _ in range(num_police_to_spawn):
                # Try to spawn police near player but not on top
                spawn_x = clamp(self.player.x + random.randint(-5, 5), 0, MAP_WIDTH - 1)
                spawn_y = clamp(self.player.y + random.randint(-5, 5), 0, MAP_HEIGHT - 1)

                if not self.game_map.get_object_at(spawn_x, spawn_y):
                    police = Enemy(spawn_x, spawn_y, "Police Officer", 60 + self.player.wanted_level * 10, 15 + self.player.wanted_level * 5, "Police")
                    self.game_map.add_object(police)
                    self.enemies[f"police_{len(self.enemies)}"] = police
                    print(f"{Fore.RED}Police arrived at ({spawn_x},{spawn_y})!{Style.RESET_ALL}")

    def game_loop(self):
        """The main loop of the game."""
        self.player.discover_area(self.game_map) # Initial discovery
        
        # Initial spawn of police if wanted level is already high from a loaded game
        if self.player.wanted_level > 0:
            self.spawn_police()

        while self.running:
            self.game_map.render(self.player)
            self.player.display_status()

            if self.player.health <= 0:
                print(f"{Fore.RED}CJ has been defeated! Game Over.{Style.RESET_ALL}")
                self.running = False
                break

            # Player needs update
            if self.game_time % 10 == 0: # Every 10 ticks, hunger/thirst decrease
                self.player.update_needs()
            
            # Wanted level decay (if not actively committing crimes)
            if self.player.wanted_level > 0 and self.game_time % 50 == 0: # Decay every 50 ticks
                self.player.reduce_wanted_level(1)

            # Police spawning based on wanted level
            if self.player.wanted_level > 0 and self.game_time % 20 == 0: # Spawn police more frequently with higher wanted level
                self.spawn_police()

            action = input("What do you do? (W/A/S/D - move, E - interact/enter, X - exit vehicle, U - use item, F - attack, V - save, L - load, Q - quit): ").lower()
            self.handle_input(action)

            # Enemy turns
            # Create a copy of values to iterate safely as enemies might be removed
            active_enemies = list(self.enemies.values()) 
            for enemy in active_enemies:
                if enemy.health > 0: # Only active enemies take turns
                    enemy.take_turn(self.player, self.game_map)
                    time.sleep(GAME_TICK_RATE / 3) # Enemies move a bit faster

            self.game_time += 1 # Advance game time
            time.sleep(GAME_TICK_RATE) # Small delay for game readability

if __name__ == "__main__":
    game = Game()
    print(f"{Fore.GREEN}Welcome to San Andreas: The Definitive Edition Demake!{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'l' to load a game or press Enter to start a new one.{Style.RESET_ALL}")
    initial_choice = input("> ").lower()
    if initial_choice == 'l':
        game.load_game()
    else:
        print(f"{Fore.GREEN}Starting a new game...{Style.RESET_ALL}")

    game.game_loop()
