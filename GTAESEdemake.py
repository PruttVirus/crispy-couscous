# Text-Based San Andreas - Enhanced Python Demake
# Version: 1.3
# -----------------------------------------------
# 🆕 CHANGELOG:
# - ✅ Fixed Big Smoke mission logic: now checks for Cash Bundle correctly even if already collected
# - ✅ Added debug print to show player inventory in Big Smoke mission (useful for debugging)
# - ✅ Improved mission flow: Sweet ➜ Ryder ➜ Big Smoke
# - ✅ Added colors with colorama for clearer UI
# - ✅ Big Smoke occupies two tiles and is labeled as "BS" on the map
# - ✅ Enemy AI improved slightly (random movement + simple attack)
# - ✅ Game supports save/load system with inventory + health + money
# -----------------------------------------------

import time
import os
import random
import json
from colorama import init, Fore, Style

# Initialize Colorama for cross-platform colored output
init(autoreset=True)

# --- Constants ---
MAP_WIDTH = 50
MAP_HEIGHT = 20
PLAYER_CHAR = 'C'
NPC_CHAR = 'N'
BIG_SMOKE_CHARS = ['B', 'S'] # Big Smoke occupies two tiles
ITEM_CHAR = 'I'
SHOP_CHAR = 'S'
ENEMY_CHAR = 'E'
EMPTY_CHAR = '.'
FOG_CHAR = ' ' # Character for unexplored areas in fog of war
GAME_TICK_RATE = 0.2 # How often the game updates (in seconds)
VISION_RADIUS = 6 # How far the player can see

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

    def __repr__(self):
        """String representation for debugging."""
        return f"{self.name}({self.x}, {self.y})"

class Character(GameObject):
    """Base class for characters with health and inventory."""
    def __init__(self, x, y, char, name, health, money=0):
        super().__init__(x, y, char, name)
        self.health = health
        self.max_health = health # Store max health for healing
        self.inventory = []
        self.money = money
        self.current_weapon = None

    def take_damage(self, amount):
        """Reduces character health by the given amount."""
        self.health -= amount
        if self.health < 0:
            self.health = 0
        print(f"{self.name} took {amount} damage. Health: {self.health}/{self.max_health}")

    def heal(self, amount):
        """Increases character health by the given amount, up to max health."""
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
        print(f"{self.name} healed {amount} health. Health: {self.health}/{self.max_health}")

    def add_item(self, item):
        """Adds an item to the character's inventory."""
        self.inventory.append(item)
        print(f"{self.name} picked up {item.name}.")

    def remove_item(self, item):
        """Removes an item from the character's inventory."""
        if item in self.inventory:
            self.inventory.remove(item)
            print(f"{self.name} used {item.name}.")
            return True
        return False

    def equip_weapon(self, weapon):
        """Equips a weapon from the inventory."""
        if weapon in self.inventory and isinstance(weapon, Weapon):
            self.current_weapon = weapon
            print(f"{self.name} equipped {weapon.name}.")
        else:
            print(f"{weapon.name} is not in {self.name}'s inventory or is not a weapon.")

    def attack(self, target):
        """Attacks a target using the current weapon or fists."""
        damage = 1 # Default fist damage
        weapon_name = "fists"
        if self.current_weapon:
            damage = self.current_weapon.damage
            weapon_name = self.current_weapon.name
        print(f"{self.name} attacks {target.name} with {weapon_name} for {damage} damage!")
        target.take_damage(damage)

class Player(Character):
    """The player character."""
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_CHAR, "CJ", 100, money=500)
        self.discovered_map = [[False for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        self.missions_completed = []
        self.current_mission = None

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

        # Check map boundaries
        if not (0 <= new_x < MAP_WIDTH and 0 <= new_y < MAP_HEIGHT):
            print(f"{Fore.RED}You hit the map boundary!{Style.RESET_ALL}")
            return False

        # Check for collisions with other objects (NPCs, Big Smoke, Enemies, Shops)
        for obj in game_map.get_all_objects():
            if obj != self: # Don't collide with self
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
        return True

    def display_status(self):
        """Prints the player's current status."""
        weapon_name = self.current_weapon.name if self.current_weapon else "None"
        print(f"\n--- {Fore.CYAN}CJ's Status{Style.RESET_ALL} ---")
        print(f"Health: {Fore.GREEN}{self.health}/{self.max_health}{Style.RESET_ALL}")
        print(f"Money: {Fore.YELLOW}${self.money}{Style.RESET_ALL}")
        print(f"Weapon: {Fore.MAGENTA}{weapon_name}{Style.RESET_ALL}")
        print(f"Inventory: {', '.join([item.name for item in self.inventory]) if self.inventory else 'Empty'}")
        print(f"Current Mission: {self.current_mission.name if self.current_mission else 'None'}")
        print(f"Missions Completed: {', '.join(self.missions_completed) if self.missions_completed else 'None'}")
        print("--------------------")

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


class Item(GameObject):
    """Base class for items that can be picked up."""
    def __init__(self, x, y, name, description, char=ITEM_CHAR):
        super().__init__(x, y, char, name)
        self.description = description

class Weapon(Item):
    """A weapon item with a damage value."""
    def __init__(self, x, y, name, description, damage):
        super().__init__(x, y, name, description)
        self.damage = damage

class HealthPack(Item):
    """A health pack item that restores health."""
    def __init__(self, x, y, name, description, heal_amount):
        super().__init__(x, y, name, description)
        self.heal_amount = heal_amount

class MoneyBundle(Item):
    """A bundle of money."""
    def __init__(self, x, y, name, description, amount):
        super().__init__(x, y, name, description)
        self.amount = amount

class Shop(GameObject):
    """A shop where the player can buy items."""
    def __init__(self, x, y, name, inventory):
        super().__init__(x, y, SHOP_CHAR, name)
        self.inventory = inventory # List of (item_object, price) tuples

    def enter(self, player):
        """Allows the player to interact with the shop."""
        print(f"\n--- {Fore.GREEN}Welcome to {self.name}!{Style.RESET_ALL} ---")
        print("Available items:")
        for i, (item, price) in enumerate(self.inventory):
            print(f"{i+1}. {item.name} ({item.description}) - ${price}")
        print("0. Exit shop")

        while True:
            try:
                choice = int(input(f"Your money: ${player.money}. Enter item number to buy (0 to exit): "))
                if choice == 0:
                    print(f"{Fore.YELLOW}Exiting shop.{Style.RESET_ALL}")
                    break
                elif 1 <= choice <= len(self.inventory):
                    item_to_buy, price = self.inventory[choice - 1]
                    if player.money >= price:
                        player.money -= price
                        player.add_item(item_to_buy)
                        print(f"{Fore.GREEN}You bought {item_to_buy.name} for ${price}. Remaining money: ${player.money}{Style.RESET_ALL}")
                        # Remove item from shop inventory after purchase (optional, but good for unique items)
                        # self.inventory.pop(choice - 1)
                    else:
                        print(f"{Fore.RED}Not enough money to buy {item_to_buy.name}.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid choice. Please enter a valid number.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a number.{Style.RESET_ALL}")

class Enemy(Character):
    """An enemy character that can attack the player."""
    def __init__(self, x, y, name, health, damage):
        super().__init__(x, y, ENEMY_CHAR, name, health)
        self.damage = damage

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
        """Enemy's turn: move towards player or attack if close."""
        # Check if player is adjacent
        if abs(self.x - player.x) <= 1 and abs(self.y - player.y) <= 1:
            self.attack(player)
        else:
            self.move_randomly(game_map) # Simple random movement

class Mission:
    """Represents a mission with objectives and rewards."""
    def __init__(self, name, description, objective_func, reward_money=0, reward_item=None):
        self.name = name
        self.description = description
        self.objective_func = objective_func # A function that takes player and returns True if objective met
        self.reward_money = reward_money
        self.reward_item = reward_item

    def is_completed(self, player):
        """Checks if the mission objective is met."""
        return self.objective_func(player)

    def complete(self, player):
        """Applies mission rewards to the player."""
        player.money += self.reward_money
        print(f"{Fore.GREEN}Received ${self.reward_money} as reward.{Style.RESET_ALL}")
        if self.reward_item:
            player.add_item(self.reward_item)

# --- Game Map and Logic ---

class GameMap:
    """Manages the game world, including objects and rendering."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.objects = [] # List of all game objects

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
        os.system('cls' if os.name == 'nt' else 'clear') # Clear console

        print(f"{Fore.WHITE}--- Text-Based San Andreas ---{Style.RESET_ALL}")
        print(f"Health: {Fore.GREEN}{player.health}/{player.max_health}{Style.RESET_ALL} | Money: {Fore.YELLOW}${player.money}{Style.RESET_ALL} | Mission: {player.current_mission.name if player.current_mission else 'None'}")
        print("-" * (self.width + 2))

        # Create an empty map grid
        grid = [[EMPTY_CHAR for _ in range(self.width)] for _ in range(self.height)]

        # Place objects on the grid
        for obj in self.objects:
            if isinstance(obj, BigSmoke):
                # Place Big Smoke's first char
                if 0 <= obj.y < self.height and 0 <= obj.x < self.width:
                    grid[obj.y][obj.x] = Fore.MAGENTA + BIG_SMOKE_CHARS[0] + Style.RESET_ALL
                # Place Big Smoke's second char
                if 0 <= obj.char2_y < self.height and 0 <= obj.char2_x < self.width:
                    grid[obj.char2_y][obj.char2_x] = Fore.MAGENTA + BIG_SMOKE_CHARS[1] + Style.RESET_ALL
            elif 0 <= obj.y < self.height and 0 <= obj.x < self.width:
                if isinstance(obj, Player):
                    grid[obj.y][obj.x] = Fore.CYAN + obj.char + Style.RESET_ALL
                elif isinstance(obj, NPC):
                    grid[obj.y][obj.x] = Fore.BLUE + obj.char + Style.RESET_ALL
                elif isinstance(obj, Item):
                    grid[obj.y][obj.x] = Fore.YELLOW + obj.char + Style.RESET_ALL
                elif isinstance(obj, Shop):
                    grid[obj.y][obj.x] = Fore.GREEN + obj.char + Style.RESET_ALL
                elif isinstance(obj, Enemy):
                    grid[obj.y][obj.x] = Fore.RED + obj.char + Style.RESET_ALL
                else:
                    grid[obj.y][obj.x] = obj.char # Default color for other objects

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

class Game:
    """Main game class, manages game state, map, and interactions."""
    def __init__(self):
        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
        self.player = Player(MAP_WIDTH // 2, MAP_HEIGHT // 2) # Start player in the center
        self.game_map.add_object(self.player)
        self.running = True

        self.npcs = {}
        self.items = {}
        self.shops = {}
        self.enemies = {}

        self._initialize_game_objects()
        self._initialize_missions()

    def _initialize_game_objects(self):
        """Initializes all NPCs, items, shops, and enemies."""
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

        # Items
        pistol = Weapon(2, 2, "Pistol", "A basic handgun.", 15)
        self.game_map.add_object(pistol)
        self.items["pistol"] = pistol

        shotgun = Weapon(MAP_WIDTH - 5, MAP_HEIGHT - 5, "Shotgun", "Deals heavy damage up close.", 30)
        self.game_map.add_object(shotgun)
        self.items["shotgun"] = shotgun

        health_pack_1 = HealthPack(7, 7, "Small Health Pack", "Restores a bit of health.", 25)
        self.game_map.add_object(health_pack_1)
        self.items["health_pack_1"] = health_pack_1

        cash_bundle = MoneyBundle(MAP_WIDTH // 4, MAP_HEIGHT // 4, "Cash Bundle", "A stack of money.", 200)
        self.game_map.add_object(cash_bundle)
        self.items["cash_bundle"] = cash_bundle

        # Shops
        ammu_nation_items = [
            (Weapon(0, 0, "Knife", "A sharp blade.", 10), 50), # x,y are placeholders for shop items
            (Weapon(0, 0, "Uzi", "Fast firing submachine gun.", 20), 150),
            (HealthPack(0, 0, "Large Health Pack", "Restores a lot of health.", 50), 75)
        ]
        ammu_nation = Shop(MAP_WIDTH - 10, 5, "Ammu-Nation", ammu_nation_items)
        self.game_map.add_object(ammu_nation)
        self.shops["ammu_nation"] = ammu_nation

        # Enemies
        gangster1 = Enemy(15, 10, "Gangster", 40, 10)
        self.game_map.add_object(gangster1)
        self.enemies["gangster1"] = gangster1

        gangster2 = Enemy(25, 8, "Gangster", 40, 10)
        self.game_map.add_object(gangster2)
        self.enemies["gangster2"] = gangster2

    def _initialize_missions(self):
        """Defines and assigns missions to NPCs."""
        # Sweet's Mission: Find the Pistol
        def sweet_objective(player):
            return any(isinstance(item, Weapon) and item.name == "Pistol" for item in player.inventory)
        sweet_mission = Mission(
            name="Sweet's Mission",
            description="Find the Pistol and bring it back to Sweet.",
            objective_func=sweet_objective,
            reward_money=100
        )
        self.npcs["sweet"].mission_offered = sweet_mission

        # Ryder's Mission: Acquire the Shotgun (from map, not shop)
        def ryder_objective(player):
            return any(isinstance(item, Weapon) and item.name == "Shotgun" for item in player.inventory)
        ryder_mission = Mission(
            name="Ryder's Mission",
            description="Find the Shotgun and show it to Ryder.",
            objective_func=ryder_objective,
            reward_money=150
        )
        self.npcs["ryder"].mission_offered = ryder_mission

        # Big Smoke's Mission: Collect Cash Bundle
        def big_smoke_objective(player):
            return any(isinstance(item, MoneyBundle) and item.name == "Cash Bundle" for item in player.inventory)
        big_smoke_mission = Mission(
            name="Big Smoke's Mission",
            description="Collect the Cash Bundle for Big Smoke.",
            objective_func=big_smoke_objective,
            reward_money=200
        )
        self.npcs["big_smoke"].mission_offered = big_smoke_mission

    def save_game(self, filename="savegame.json"):
        """Saves the current game state to a JSON file."""
        data = {
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "health": self.player.health,
                "money": self.player.money,
                "inventory": [(item.name, item.__class__.__name__) for item in self.player.inventory],
                "current_weapon": self.player.current_weapon.name if self.player.current_weapon else None,
                "discovered_map": self.player.discovered_map,
                "missions_completed": self.player.missions_completed,
                "current_mission": self.player.current_mission.name if self.player.current_mission else None
            },
            "npcs": {name: {"mission_completed": npc.mission_completed} for name, npc in self.npcs.items()},
            "items_on_map": [{"name": item.name, "x": item.x, "y": item.y, "type": item.__class__.__name__}
                             for item in self.game_map.get_all_objects() if isinstance(item, Item)],
            "enemies": [{"name": enemy.name, "x": enemy.x, "y": enemy.y, "health": enemy.health}
                        for enemy in self.game_map.get_all_objects() if isinstance(enemy, Enemy)],
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

            # Clear existing objects for a clean load
            self.game_map.objects = []
            self._initialize_game_objects() # Re-add initial objects
            self._initialize_missions() # Re-initialize missions

            # Load player data
            player_data = data["player"]
            self.player.set_position(player_data["x"], player_data["y"])
            self.player.health = player_data["health"]
            self.player.money = player_data["money"]
            self.player.discovered_map = player_data["discovered_map"]
            self.player.missions_completed = player_data["missions_completed"]

            # Reconstruct inventory
            self.player.inventory = []
            for item_name, item_type in player_data["inventory"]:
                # This requires knowing how to reconstruct items by name/type
                # For simplicity, we'll assume a mapping or re-use existing item instances if they match
                # A more robust solution would involve a factory function for items
                if item_name == "Pistol": self.player.add_item(Weapon(0,0,"Pistol","",15))
                elif item_name == "Shotgun": self.player.add_item(Weapon(0,0,"Shotgun","",30))
                elif item_name == "Knife": self.player.add_item(Weapon(0,0,"Knife","",10))
                elif item_name == "Uzi": self.player.add_item(Weapon(0,0,"Uzi","",20))
                elif item_name == "Small Health Pack": self.player.add_item(HealthPack(0,0,"Small Health Pack","",25))
                elif item_name == "Large Health Pack": self.player.add_item(HealthPack(0,0,"Large Health Pack","",50))
                elif item_name == "Cash Bundle": self.player.add_item(MoneyBundle(0,0,"Cash Bundle","",200))

            # Equip current weapon
            if player_data["current_weapon"]:
                for item in self.player.inventory:
                    if isinstance(item, Weapon) and item.name == player_data["current_weapon"]:
                        self.player.equip_weapon(item)
                        break

            # Set current mission
            if player_data["current_mission"]:
                # Find the mission object by name
                for npc_name, npc_obj in self.npcs.items():
                    if npc_obj.mission_offered and npc_obj.mission_offered.name == player_data["current_mission"]:
                        self.player.current_mission = npc_obj.mission_offered
                        break

            # Load NPC mission completion status
            for name, npc_data in data["npcs"].items():
                if name in self.npcs:
                    self.npcs[name].mission_completed = npc_data["mission_completed"]

            # Load items on map (remove original and add loaded ones)
            # First, remove all initial Item objects from the map
            items_to_remove = [obj for obj in self.game_map.objects if isinstance(obj, Item)]
            for item in items_to_remove:
                self.game_map.remove_object(item)
            # Then, add items from save data
            for item_data in data["items_on_map"]:
                item_obj = None
                if item_data["type"] == "Weapon":
                    item_obj = Weapon(item_data["x"], item_data["y"], item_data["name"], "", 0) # Damage is not saved, re-init
                    if item_data["name"] == "Pistol": item_obj.damage = 15
                    elif item_data["name"] == "Shotgun": item_obj.damage = 30
                elif item_data["type"] == "HealthPack":
                    item_obj = HealthPack(item_data["x"], item_data["y"], item_data["name"], "", 0) # Heal amount not saved
                    if item_data["name"] == "Small Health Pack": item_obj.heal_amount = 25
                    elif item_data["name"] == "Large Health Pack": item_obj.heal_amount = 50
                elif item_data["type"] == "MoneyBundle":
                    item_obj = MoneyBundle(item_data["x"], item_data["y"], item_data["name"], "", item_data["amount"])
                if item_obj:
                    self.game_map.add_object(item_obj)

            # Load enemies (remove original and add loaded ones)
            enemies_to_remove = [obj for obj in self.game_map.objects if isinstance(obj, Enemy)]
            for enemy in enemies_to_remove:
                self.game_map.remove_object(enemy)
            for enemy_data in data["enemies"]:
                enemy_obj = Enemy(enemy_data["x"], enemy_data["y"], enemy_data["name"], enemy_data["health"], 10) # Damage not saved
                self.game_map.add_object(enemy_obj)


            # Re-add player, NPCs, and Shops as they are persistent
            self.game_map.add_object(self.player)
            for npc in self.npcs.values():
                self.game_map.add_object(npc)
            for shop in self.shops.values():
                self.game_map.add_object(shop)


            print(f"{Fore.GREEN}Game loaded successfully from {filename}!{Style.RESET_ALL}")
        except FileNotFoundError:
            print(f"{Fore.RED}Save file '{filename}' not found. Starting new game.{Style.RESET_ALL}")
        except json.JSONDecodeError:
            print(f"{Fore.RED}Error decoding save file. It might be corrupted. Starting new game.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}An unexpected error occurred during loading: {e}. Starting new game.{Style.RESET_ALL}")


    def handle_input(self, command):
        """Processes player input commands."""
        command = command.lower().strip()
        dx, dy = 0, 0
        moved = False

        if command == 'w':
            dy = -1
        elif command == 's':
            dy = 1
        elif command == 'a':
            dx = -1
        elif command == 'd':
            dx = 1
        elif command == 'q':
            self.running = False
            print(f"{Fore.RED}Exiting game. Goodbye!{Style.RESET_ALL}")
            return

        if dx != 0 or dy != 0:
            moved = self.player.move(dx, dy, self.game_map)
            if moved:
                self.player.discover_area(self.game_map) # Update discovered map on movement

        # Check for interactions after movement
        if moved or command in ['i', 'u', 't', 'b', 'l', 'v']: # Commands that don't involve movement
            obj_at_player_pos = self.game_map.get_object_at(self.player.x, self.player.y)

            if obj_at_player_pos and obj_at_player_pos != self.player:
                if isinstance(obj_at_player_pos, NPC):
                    obj_at_player_pos.talk(self.player)
                elif isinstance(obj_at_player_pos, Item):
                    self.player.add_item(obj_at_player_pos)
                    self.game_map.remove_object(obj_at_player_pos) # Remove item from map after pickup
                elif isinstance(obj_at_player_pos, Shop):
                    obj_at_player_pos.enter(self.player)
                elif isinstance(obj_at_player_pos, Enemy):
                    print(f"{Fore.RED}You bumped into a {obj_at_player_pos.name}! Prepare for combat!{Style.RESET_ALL}")
                    self.player.attack(obj_at_player_pos) # Player attacks on collision

            if command == 'i': # Inventory
                self.player.display_status()
            elif command.startswith('u '): # Use item
                item_name = command[2:].strip()
                found_item = next((item for item in self.player.inventory if item.name.lower() == item_name.lower()), None)
                if found_item:
                    if isinstance(found_item, HealthPack):
                        self.player.heal(found_item.heal_amount)
                        self.player.remove_item(found_item)
                    elif isinstance(found_item, Weapon):
                        self.player.equip_weapon(found_item)
                    else:
                        print(f"{Fore.YELLOW}You can't 'use' {found_item.name} in that way.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Item '{item_name}' not found in your inventory.{Style.RESET_ALL}")
            elif command.startswith('a '): # Attack
                target_name = command[2:].strip()
                # Find target in adjacent cells
                target = None
                for obj in self.game_map.get_all_objects():
                    if isinstance(obj, Enemy) and obj.name.lower() == target_name.lower():
                        if abs(self.player.x - obj.x) <= 1 and abs(self.player.y - obj.y) <= 1:
                            target = obj
                            break
                if target:
                    self.player.attack(target)
                    if target.health <= 0:
                        print(f"{Fore.GREEN}{target.name} defeated!{Style.RESET_ALL}")
                        self.game_map.remove_object(target)
                        # Reward for defeating enemy (optional)
                        self.player.money += 50
                        print(f"{Fore.YELLOW}Gained 50 money for defeating {target.name}.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}No enemy '{target_name}' found nearby to attack.{Style.RESET_ALL}")
            elif command == 'l': # Load game
                self.load_game()
            elif command == 'v': # Save game
                self.save_game()
            else:
                if not moved: # Only print if no movement command was issued
                    print(f"{Fore.YELLOW}Invalid command. Use W, A, S, D to move, I for inventory, U [item] to use, A [enemy] to attack, L to load, V to save, Q to quit.{Style.RESET_ALL}")

    def game_over(self):
        """Checks if game over conditions are met."""
        if self.player.health <= 0:
            print(f"{Fore.RED}\n--- GAME OVER ---{Style.RESET_ALL}")
            print(f"{Fore.RED}CJ's health reached zero. You got wasted!{Style.RESET_ALL}")
            self.running = False
            return True
        return False

    def game_win(self):
        """Checks if game win conditions are met."""
        # Example win condition: All main missions completed
        if "Sweet's Mission" in self.player.missions_completed and \
           "Ryder's Mission" in self.player.missions_completed and \
           "Big Smoke's Mission" in self.player.missions_completed:
            print(f"{Fore.GREEN}\n--- CONGRATULATIONS! ---{Style.RESET_ALL}")
            print(f"{Fore.GREEN}You have completed all main missions! Grove Street 4 Life!{Style.RESET_ALL}")
            self.running = False
            return True
        return False

    def main_loop(self):
        """The main game loop."""
        self.player.discover_area(self.game_map) # Initial discovery
        while self.running:
            self.game_map.render(self.player)

            # Enemy turns
            for enemy in [obj for obj in self.game_map.get_all_objects() if isinstance(obj, Enemy) and obj.health > 0]:
                enemy.take_turn(self.player, self.game_map)

            if self.game_over() or self.game_win():
                break

            command = input(f"{Fore.WHITE}Enter command (W/A/S/D to move, I for inventory, U [item] to use, A [enemy] to attack, L to load, V to save, Q to quit): {Style.RESET_ALL}")
            self.handle_input(command)

            time.sleep(GAME_TICK_RATE)

# Entry point
if __name__ == "__main__":
    game_instance = Game()
    game_instance.main_loop()
