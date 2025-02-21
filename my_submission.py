from collections import defaultdict, deque
import random
from typing import Optional, Tuple, Union, cast
from risk_helper.game import Game
from risk_shared.models.card_model import CardModel
from risk_shared.queries.query_attack import QueryAttack
from risk_shared.queries.query_claim_territory import QueryClaimTerritory
from risk_shared.queries.query_defend import QueryDefend
from risk_shared.queries.query_distribute_troops import QueryDistributeTroops
from risk_shared.queries.query_fortify import QueryFortify
from risk_shared.queries.query_place_initial_troop import QueryPlaceInitialTroop
from risk_shared.queries.query_redeem_cards import QueryRedeemCards
from risk_shared.queries.query_troops_after_attack import QueryTroopsAfterAttack
from risk_shared.queries.query_type import QueryType
from risk_shared.records.moves.move_attack import MoveAttack
from risk_shared.records.moves.move_attack_pass import MoveAttackPass
from risk_shared.records.moves.move_claim_territory import MoveClaimTerritory
from risk_shared.records.moves.move_defend import MoveDefend
from risk_shared.records.moves.move_distribute_troops import MoveDistributeTroops
from risk_shared.records.moves.move_fortify import MoveFortify
from risk_shared.records.moves.move_fortify_pass import MoveFortifyPass
from risk_shared.records.moves.move_place_initial_troop import MovePlaceInitialTroop
from risk_shared.records.moves.move_redeem_cards import MoveRedeemCards
from risk_shared.records.moves.move_troops_after_attack import MoveTroopsAfterAttack
from risk_shared.records.record_attack import RecordAttack
from risk_shared.records.types.move_type import MoveType


# We will store our enemy in the bot state.
class BotState():
    def __init__(self):
        self.enemy: Optional[int] = None


def main():
    
    # Get the game object, which will connect you to the engine and
    # track the state of the game.
    game = Game()
    bot_state = BotState()
   
    # Respond to the engine's queries with your moves.
    while True:

        # Get the engine's query (this will block until you receive a query).
        query = game.get_next_query()

        # Based on the type of query, respond with the correct move.
        def choose_move(query: QueryType) -> MoveType:
            match query:
                case QueryClaimTerritory() as q:
                    return handle_claim_territory(game, bot_state, q)

                case QueryPlaceInitialTroop() as q:
                    return handle_place_initial_troop(game, bot_state, q)

                case QueryRedeemCards() as q:
                    return handle_redeem_cards(game, bot_state, q)

                case QueryDistributeTroops() as q:
                    return handle_distribute_troops(game, bot_state, q)

                case QueryAttack() as q:
                    return handle_attack(game, bot_state, q)

                case QueryTroopsAfterAttack() as q:
                    return handle_troops_after_attack(game, bot_state, q)

                case QueryDefend() as q:
                    return handle_defend(game, bot_state, q)

                case QueryFortify() as q:
                    return handle_fortify(game, bot_state, q)
        
        # Send the move to the engine.
        game.send_move(choose_move(query))
                

def handle_claim_territory(game: Game, bot_state: BotState, query: QueryClaimTerritory) -> MoveClaimTerritory:
    """At the start of the game, you can claim a single unclaimed territory every turn 
    until all the territories have been claimed by players."""

    country_dictionary = {
        "North America": list(range(9)),
        "South America": list(range(29, 32)),
        "Europe": list(range(9, 16)),
        "Africa": list(range(32, 38)),
        "Asia": list(range(16, 29)),
        "Australia": list(range(38, 43))
    }
    country_joint_dictionary = {
        "North America": [0, 2, 4],
        "South America": [30, 29],
        "Australia": [40],
        "Africa": [33, 34, 36],
        "Asia": [16, 21, 22, 24, 26],
        "Europe": [10, 12, 13, 14, 15]

    }
    continent_list = ["North America", "South America", "Australia", "Africa" ,"Europe", "Asia"]

    unclaimed_territories = game.state.get_territories_owned_by(None)
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)

    def is_continent_contested(continent: str) -> bool:
        """Check if a continent has any territory occupied by other players."""
        continent_territories = country_dictionary[continent]
        for territory in continent_territories:
            if territory in game.state.territories and game.state.territories[territory].occupier not in [None, game.state.me.player_id]:
                return True
        return False

    for continent, joint_territories in country_joint_dictionary.items():
        if not is_continent_contested(continent):
            available = list(set(unclaimed_territories) & set(joint_territories))
            if available:
                selected_territory = available[0]
                game.move_claim_territory(query, selected_territory)

                # 占领关键节点后优先占领对应大洲的其他领土
                continent_territories = country_dictionary[continent]
                available_continent_territories = list(set(unclaimed_territories) & set(continent_territories))
                if available_continent_territories:
                    selected_territory = available_continent_territories[0]
                    return game.move_claim_territory(query, selected_territory)

    adjacent_territories = game.state.get_all_adjacent_territories(my_territories)

    def is_player_close_to_continent_control(player_id: int) -> bool:
        for continent, territories in country_dictionary.items():
            player_territories = [territory for territory in territories if territory in game.state.territories and game.state.territories[territory].occupier == player_id]
            if len(player_territories) >= len(territories) * 0.75:  
                return True
        return False

    for player_id in game.state.players.keys():
        if player_id != game.state.me.player_id and is_player_close_to_continent_control(player_id):

            for continent in continent_list:
                continent_territories = country_dictionary[continent]
                available = list(set(unclaimed_territories) & set(continent_territories))
                if available:
                    selected_territory = available[0]
                    return game.move_claim_territory(query, selected_territory)
    
    for continent, territories in country_dictionary.items():
        if any(territory in my_territories for territory in territories):
            available = list(set(unclaimed_territories) & set(territories))
            if available:
                selected_territory = available[0]
                return game.move_claim_territory(query, selected_territory)


    available = list(set(unclaimed_territories) & set(adjacent_territories))
    if len(available) != 0:

        def count_adjacent_friendly(x: int) -> int:
            return len(set(my_territories) & set(game.state.map.get_adjacent_to(x)))

        selected_territory = sorted(available, key=lambda x: count_adjacent_friendly(x), reverse=True)[0]
    else:
        selected_territory = sorted(unclaimed_territories, key=lambda x: len(game.state.map.get_adjacent_to(x)), reverse=True)[0]

    return game.move_claim_territory(query, selected_territory)


def handle_place_initial_troop(game: Game, bot_state: BotState, query: QueryPlaceInitialTroop) -> MovePlaceInitialTroop:
    """After all the territories have been claimed, you can place a single troop on one
    of your territories each turn until each player runs out of troops."""
    all_territories = game.state.get_territories_owned_by(game.state.me.player_id)
    country_dictionary = {
        "North America":list(range(9)),
        "South America":list(range(29, 32)),
        "Europe": list(range(9, 16)),
        "Africa": list(range(32, 38)),
        "Asia": list(range(16,29)),
        "Australia": list(range(38,43))
    }
    joint_list = [0,2,4,30,29,10,12,13,14,15,33,34,36,16,21,22,24,26,40]
    continent_list = ["North America", "South America", "Australia", "Africa" ,"Europe", "Asia"]
    
    # We will place troops along the territories on our border.
    border_territories = game.state.get_all_border_territories(
        game.state.get_territories_owned_by(game.state.me.player_id)
    )

    # We will place a troop in the border territory with the biggest difference in troops comparing to 
    # the adjacent enemy territories 

    border_territory_models = [game.state.territories[x] for x in border_territories]
    

    # all joint country need at least 3 troops
    for joint in joint_list:
        if joint in all_territories:
            if game.state.territories[joint].troops < 3:
                return game.move_place_initial_troop(query, joint)

    # all boarder country need at least 2 troops
    for border_territory in border_territory_models:
        if border_territory.troops < 2:
            return game.move_place_initial_troop(query, border_territory.territory_id)

    # rest of the troops goes to the border of the most percentage continent
    def calculate_continent_progress(all_territory: list[int], country_dictionary: dict[str, list[int]], continent_list: list[str]) -> list[float]:
        territory_percentage = []
        for continent in continent_list:
            owned_territory = 0
            unowned_territory = 0
            continent_territory = country_dictionary[continent]
            for territory in continent_territory:
                if territory in all_territory:
                    owned_territory += 1
                else:
                    unowned_territory += 1
            percentage = owned_territory/(owned_territory + unowned_territory)
            territory_percentage.append(percentage)
        return territory_percentage

    
    continent_progress = calculate_continent_progress(all_territories, country_dictionary, continent_list)
    
    # find maximum percentage continent that is not 100%
    max_percentage = 0
    max_percentage_continent = ''
    for i, percentage in enumerate(continent_progress):
        if percentage > max_percentage and percentage != 1:
            max_percentage = percentage
            max_percentage_continent = continent_list[i]
    
    # all in one of the boarder territory, prioritise joint
    border_territory_in_max_continent = []
    for border_territory in border_territories:

        if border_territory in country_dictionary[max_percentage_continent]:
            border_territory_in_max_continent.append(border_territory)

            if border_territory in joint_list:
                return game.move_place_initial_troop(query, border_territory)
    
    return game.move_place_initial_troop(query, border_territory_in_max_continent[0])


def handle_redeem_cards(game: Game, bot_state: BotState, query: QueryRedeemCards) -> MoveRedeemCards:
    """After the claiming and placing initial troops phases are over, you can redeem any
    cards you have at the start of each turn, or after killing another player."""

    # We will always redeem the minimum number of card sets we can until the 12th card set has been redeemed.
    # This is just an arbitrary choice to try and save our cards for the late game.

    # We always have to redeem enough cards to reduce our card count below five.
    card_sets: list[Tuple[CardModel, CardModel, CardModel]] = []
    cards_remaining = game.state.me.cards.copy()

    while len(cards_remaining) >= 5:
        card_set = game.state.get_card_set(cards_remaining)
        # According to the pigeonhole principle, we should always be able to make a set
        # of cards if we have at least 5 cards.
        assert card_set != None
        card_sets.append(card_set)
        cards_remaining = [card for card in cards_remaining if card not in card_set]

    # Remember we can't redeem any more than the required number of card sets if 
    # we have just eliminated a player.
    if game.state.card_sets_redeemed > 12 and query.cause == "turn_started":
        card_set = game.state.get_card_set(cards_remaining)
        while card_set != None:
            card_sets.append(card_set)
            cards_remaining = [card for card in cards_remaining if card not in card_set]
            card_set = game.state.get_card_set(cards_remaining)

    return game.move_redeem_cards(query, [(x[0].card_id, x[1].card_id, x[2].card_id) for x in card_sets])


def handle_distribute_troops(game: Game, bot_state: BotState, query: QueryDistributeTroops) -> MoveDistributeTroops:
    """After you redeem cards (you may have chosen to not redeem any), you need to distribute
    all the troops you have available across your territories. This can happen at the start of
    your turn or after killing another player.
    """

    # We will distribute troops across our border territories.
    total_troops = game.state.me.troops_remaining
    distributions = defaultdict(lambda: 0)
    border_territories = game.state.get_all_border_territories(
        game.state.get_territories_owned_by(game.state.me.player_id)
    )
    all_territories = game.state.get_territories_owned_by(game.state.me.player_id)



    # We need to remember we have to place our matching territory bonus
    # if we have one.
    if len(game.state.me.must_place_territory_bonus) != 0:
        assert total_troops >= 2
        distributions[game.state.me.must_place_territory_bonus[0]] += 2
        total_troops -= 2


    # We will equally distribute across border territories in the early game,
    # but start doomstacking in the late game.
    country_dictionary = {
        "North America":list(range(9)),
        "South America":list(range(29, 32)),
        "Australia": list(range(38,43)),
        "Africa": list(range(32, 38)),
        "Europe": list(range(9, 16)),
        "Asia": list(range(16,29)),
    }
    country_joint_dictionary = {
        "North America":[0,2,4],
        "South America":[30,29],
        "Australia": [40],
        "Africa": [33,34,36],
        "Europe": [10,12,13,14,15],
        "Asia": [16,21,22,24,26],
    }

    continent_list = ["North America", "South America", "Australia", "Africa" ,"Europe", "Asia"]

    #calculate if there is any continent that has been completely dominated
    def calculate_continent_progress(all_territory: list[int], country_dictionary: dict[str, list[int]], continent_list: list[str]) -> list[float]:
        territory_percentage = []
        for continent in continent_list:
            owned_territory = 0
            unowned_territory = 0
            continent_territory = country_dictionary[continent]
            for territory in continent_territory:
                if territory in all_territory:
                    owned_territory += 1
                else:
                    unowned_territory += 1
            percentage = owned_territory/(owned_territory + unowned_territory)
            territory_percentage.append(percentage)
        return territory_percentage

    
    continent_progress = calculate_continent_progress(all_territories, country_dictionary, continent_list)
    captured_continent = []

    i = 0
    while i < len(continent_progress):
        if continent_progress[i] == 1.0:
            captured_continent.append(continent_list[i])
        i += 1

    all_joint_territory = []
    for continent in captured_continent:

        #include all the joint territory that need to be reinforced if next to opponent territory
        all_joint_territory += country_joint_dictionary[continent]
        
    if len(game.state.recording) < 4000:
        if len(all_joint_territory) != 0:

            if "North America" in captured_continent:
                if "South America" in captured_continent:
                    all_joint_territory.remove(30)
                    all_joint_territory.remove(2)
                if "Asia" in captured_continent:
                    all_joint_territory.remove(0)
                    all_joint_territory.remove(21)
                if "Europe" in captured_continent:
                    all_joint_territory.remove(4)
                    all_joint_territory.remove(10)
            if "South America" in captured_continent:
                if "Africa" in captured_continent:
                    all_joint_territory.remove(29)
                    all_joint_territory.remove(36)
            if "Europe" in captured_continent:
                if "Asia" in captured_continent:
                    all_joint_territory.remove(13)
                    all_joint_territory.remove(14)
                    all_joint_territory.remove(16)
                    all_joint_territory.remove(22)
                    all_joint_territory.remove(26)
                    if "Africa" in captured_continent:              
                        all_joint_territory.remove(15)
                        all_joint_territory.remove(34)
                        all_joint_territory.remove(36)
            if "Asia" in captured_continent:
                if "Australia" in captured_continent:
                    all_joint_territory.remove(24)
                    all_joint_territory.remove(40)
            if len(all_joint_territory) != 0:
                troops_per_territory = total_troops // len(all_joint_territory)
                leftover_troops = total_troops % len(all_joint_territory)
                for territory in all_joint_territory:
                    distributions[territory] += troops_per_territory
                distributions[border_territories[0]] += leftover_troops
            else:
                distributions[border_territories[0]] += total_troops
        else:
            #if we did not have any continent, we try to stack on the continent with greatest friendly territory, and conquer the entire continent
            max_percentage = 0
            max_continent = ""
            count = 0
            while count < len(continent_progress):
                if continent_progress[count] >= max_percentage:
                    max_continent = continent_list[count]
                count += 1

            reinforce_territory = []
            for territory in border_territories:
                if territory in country_dictionary[max_continent]:
                    reinforce_territory.append(territory)

            if len(reinforce_territory) != 0:
                troops_per_territory = total_troops // len(reinforce_territory)
                leftover_troops = total_troops % len(reinforce_territory)
                for territory in reinforce_territory:
                    distributions[territory] += troops_per_territory
        
                # The leftover troops will be put some territory (we don't care)
                distributions[border_territories[0]] += leftover_troops
            else:
                distributions[border_territories[0]] += total_troops

    else:
        my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
        weakest_players = sorted(game.state.players.values(), key=lambda x: sum(
            [game.state.territories[y].troops for y in game.state.get_territories_owned_by(x.player_id)]
        ))

        for player in weakest_players:
            bordering_enemy_territories = set(game.state.get_all_adjacent_territories(my_territories)) & set(game.state.get_territories_owned_by(player.player_id))
            if len(bordering_enemy_territories) > 0:
                print("my territories", [game.state.map.get_vertex_name(x) for x in my_territories])
                print("bordering enemies", [game.state.map.get_vertex_name(x) for x in bordering_enemy_territories])
                print("adjacent to target", [game.state.map.get_vertex_name(x) for x in game.state.map.get_adjacent_to(list(bordering_enemy_territories)[0])])
                selected_territory = list(set(game.state.map.get_adjacent_to(list(bordering_enemy_territories)[0])) & set(my_territories))[0]
                distributions[selected_territory] += total_troops
                break


    return game.move_distribute_troops(query, distributions)


def handle_attack(game: Game, bot_state: BotState, query: QueryAttack) -> Union[MoveAttack, MoveAttackPass]:
    """After the troop phase of your turn, you may attack any number of times until you decide to
    stop attacking (by passing). After a successful attack, you may move troops into the conquered
    territory. If you eliminated a player you will get a move to redeem cards and then distribute troops."""
    
    # We will attack someone.
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
    bordering_territories = game.state.get_all_adjacent_territories(my_territories)

    def attack_weakest(territories: list[int]) -> Optional[MoveAttack]:
        # We will attack the weakest territory from the list.
        territories = sorted(territories, key=lambda x: game.state.territories[x].troops)
        for candidate_target in territories:
            candidate_attackers = sorted(list(set(game.state.map.get_adjacent_to(candidate_target)) & set(my_territories)), key=lambda x: game.state.territories[x].troops, reverse=True)
            for candidate_attacker in candidate_attackers:
                if game.state.territories[candidate_attacker].troops > 1:
                    return game.move_attack(query, candidate_attacker, candidate_target, min(3, game.state.territories[candidate_attacker].troops - 1))


    if len(game.state.recording) < 4000:
        # We will check if anyone attacked us in the last round.
        new_records = game.state.recording[game.state.new_records:]
        enemy = None
        for record in new_records:
            match record:
                case MoveAttack() as r:
                    if r.defending_territory in set(my_territories):
                        enemy = r.move_by_player

        # If we don't have an enemy yet, or we feel angry, this player will become our enemy.
        if enemy != None:
            if bot_state.enemy == None or random.random() < 0.05:
                bot_state.enemy = enemy
        
        # If we have no enemy, we will pick the player with the weakest territory bordering us, and make them our enemy.
        else:
            weakest_territory = min(bordering_territories, key=lambda x: game.state.territories[x].troops)
            bot_state.enemy = game.state.territories[weakest_territory].occupier
            
        # We will attack their weakest territory that gives us a favourable battle if possible.
        enemy_territories = list(set(bordering_territories) & set(game.state.get_territories_owned_by(enemy)))
        move = attack_weakest(enemy_territories)
        if move != None:
            return move
        
        # Otherwise we will attack anyone most of the time.
        if random.random() < 0.8:
            move = attack_weakest(bordering_territories)
            if move != None:
                return move

    # In the late game, we will attack anyone adjacent to our strongest territories (hopefully our doomstack).
    else:
        strongest_territories = sorted(my_territories, key=lambda x: game.state.territories[x].troops, reverse=True)
        for territory in strongest_territories:
            move = attack_weakest(list(set(game.state.map.get_adjacent_to(territory)) - set(my_territories)))
            if move != None:
                return move

    return game.move_attack_pass(query)


def handle_troops_after_attack(game: Game, bot_state: BotState, query: QueryTroopsAfterAttack) -> MoveTroopsAfterAttack:
    """After conquering a territory in an attack, you must move troops to the new territory."""
    
    # First we need to get the record that describes the attack, and then the move that specifies
    # which territory was the attacking territory.
    record_attack = cast(RecordAttack, game.state.recording[query.record_attack_id])
    move_attack = cast(MoveAttack, game.state.recording[record_attack.move_attack_id])

    # We will always move the maximum number of troops we can.
    return game.move_troops_after_attack(query, game.state.territories[move_attack.attacking_territory].troops - 1)


def handle_defend(game: Game, bot_state: BotState, query: QueryDefend) -> MoveDefend:
    """If you are being attacked by another player, you must choose how many troops to defend with."""

    # We will always defend with the most troops that we can.

    # First we need to get the record that describes the attack we are defending against.
    move_attack = cast(MoveAttack, game.state.recording[query.move_attack_id])
    defending_territory = move_attack.defending_territory
    
    # We can only defend with up to 2 troops, and no more than we have stationed on the defending
    # territory.
    defending_troops = min(game.state.territories[defending_territory].troops, 2)
    return game.move_defend(query, defending_troops)


def handle_fortify(game: Game, bot_state: BotState, query: QueryFortify) -> Union[MoveFortify, MoveFortifyPass]:
    """At the end of your turn, after you have finished attacking, you may move a number of troops between
    any two of your territories (they must be adjacent)."""


    # We will always fortify towards the most powerful player (player with most troops on the map) to defend against them.
    my_territories = game.state.get_territories_owned_by(game.state.me.player_id)
    total_troops_per_player = {}
    for player in game.state.players.values():
        total_troops_per_player[player.player_id] = sum([game.state.territories[x].troops for x in game.state.get_territories_owned_by(player.player_id)])

    most_powerful_player = max(total_troops_per_player.items(), key=lambda x: x[1])[0]

    # If we are the most powerful, we will pass.
    if most_powerful_player == game.state.me.player_id:
        return game.move_fortify_pass(query)
    
    # Otherwise we will find the shortest path between our territory with the most troops
    # and any of the most powerful player's territories and fortify along that path.
    candidate_territories = game.state.get_all_border_territories(my_territories)
    most_troops_territory = max(candidate_territories, key=lambda x: game.state.territories[x].troops)

    # To find the shortest path, we will use a custom function.
    shortest_path = find_shortest_path_from_vertex_to_set(game, most_troops_territory, set(game.state.get_territories_owned_by(most_powerful_player)))
    # We will move our troops along this path (we can only move one step, and we have to leave one troop behind).
    # We have to check that we can move any troops though, if we can't then we will pass our turn.
    if len(shortest_path) > 0 and game.state.territories[most_troops_territory].troops > 1:
        return game.move_fortify(query, shortest_path[0], shortest_path[1], game.state.territories[most_troops_territory].troops - 1)
    else:
        return game.move_fortify_pass(query)


def find_shortest_path_from_vertex_to_set(game: Game, source: int, target_set: set[int]) -> list[int]:
    """Used in move_fortify()."""

    # We perform a BFS search from our source vertex, stopping at the first member of the target_set we find.
    queue = deque()
    queue.appendleft(source)

    current = queue.pop()
    parent = {}
    seen = {current: True}

    while len(queue) != 0:
        if current in target_set:
            break

        for neighbour in game.state.map.get_adjacent_to(current):
            if neighbour not in seen:
                seen[neighbour] = True
                parent[neighbour] = current
                queue.appendleft(neighbour)

        current = queue.pop()

    path = []
    while current in parent:
        path.append(current)
        current = parent[current]

    return path[::-1]

if __name__ == "__main__":
    main()