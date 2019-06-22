"""
Usefull tool box to store some functions call by TelloEDu and Swarm functions

"""

__all__ = ['reverse_actions', 'back_to_base', 'command_from_key']

def reverse_actions(actions: list):
    """
    Reverse the action list to an other action list with opposite cammands
    Mission Pad ID commands are not supported yet
    """

    reversed_list = []
    #Ignorable statements
    ign_statements = ['command', 'streamon', 'streamoff', 'mon', 'moff', 'sn?', 'battery?', 'time?', 'wifi?', 'sdk?']
    #Dict to swap actions
    contrary_dict = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left', 'forward': 'back', 'back': 'forward', 'cw': 'ccw', 'ccw':'cw', 'land': 'takeoff', 'emergency': 'takeoff', 'takeoff': 'land'}
    flip_contrary_dict = {'l': 'r', 'r': 'l', 'f':'b', 'b':'f'}
    #Complex actions / jump is using MID
    complex_actions = ['go', 'curve', 'jump']

    for action in actions[::-1]:
        try:
            drone_id = action.split('-')[0] + '-'
            command = action.split('-')[1].split(' ')[0]
        except IndexError:
            # TelloEDU not using drone index
            drone_id = ''
            command = action
        values = []
        if command in ign_statements:
            print('out : ' +command)
            continue
        #If this is a command with parameters
        if len(action.split(' ')) > 1:
            values = action.split('-')[1].split(' ')[1:]
        #If there is a simple contrary already in the dict
        if command in contrary_dict.keys():
            if values:
                action = drone_id + contrary_dict[command] + ' ' + ' '.join(values)
            else:
                #Useful for flips
                action = drone_id + contrary_dict[command]
        elif command in complex_actions:
            if command == 'go':
                #Only reverse x and y   (put 3 to also reverse the z)
                for index, value in enumerate(values[:3]):
                    values[index] = str(-1 * int(value))
                action = drone_id + 'go ' + ' '.join(values)
            if command == 'curve':
                #Not implemented yet
                action = 'Undefined curve'
        else:
            #It should be a flip
            if command == 'flip':
                action = drone_id + 'flip ' + flip_contrary_dict[values[0]]
            else:
                print('Error with command: ' + command)

        reversed_list.append(action)
    return reversed_list

def back_to_base(func):
    """ Decorator for all drone manipulation modes """
    def wrapper(self, *args, **kwargs):
        if not self.swarm.end_connection:
            res = func(self, *args, **kwargs)
            if self.swarm.back_to_base:
                self.swarm.execute_actions(reverse_actions(self.swarm.all_instructions))
                print('Drone should be back at the base')
            print('Mission completed')
            self.swarm.end_connection = True
            return res
        return None
    return wrapper

def command_from_key(key):
    """Return the command correspondign to the key typed (like a giant dictionnary)"""
    dict_int_commands = {111: 'forward 30', 113: 'left 30', 114: 'right 30', 116: 'back 30'}
    dict_str_commands = {'a': 'sn?', ' ': 'takeoff', '+' : 'land', '8': 'up 30', '2': 'down 30', '6': 'cw 30',
          '4': 'ccw 30', 'b': 'battery?', 'f': 'flip f', 'H': 'forward 30', 'A': 'forward 30', 'M': 'right 30',
          'C': 'right 30', 'P': 'back 30', 'B': 'back 30', 'K': 'left 30', 'D': 'left 30'}

    res_action = dict_int_commands.get(key)
    if res_action is None:
        return dict_str_commands.get(key)
    return res_action

