import random
from extension.board_utils import list_legal_moves_for

# used this for testing my agent, the random one was too easy
values = {"Pawn": 1, "Knight": 3, "Bishop": 3, "Right": 8, "Queen": 9, "King": 100}


def randomOpponent(board, player, var):
    legal = list_legal_moves_for(board, player)
    if legal:
        return random.choice(legal)
    return None, None


def opponent(board, player, var):
    """"
    Greedy opponent - takes the most valuable piece it can, otherwise random move
    """
    piece, move_opt = None, None
    print(f"Ply: {var[0]}")

    legal = list_legal_moves_for(board, player)
    if not legal:
        return piece, move_opt

    bestValue = 0
    bestMoves = []
    for pc, opt in legal:
        gain = 0
        for pos in opt.captures:
            victim = board[pos].piece
            if victim is not None:
                gain += values.get(victim.name, 0)
        if gain > bestValue:
            bestValue = gain
            bestMoves = [(pc, opt)]
        elif gain == bestValue and gain > 0:
            bestMoves.append((pc, opt))

    if bestMoves:
        piece, move_opt = random.choice(bestMoves)
    else:
        piece, move_opt = random.choice(legal)

    return piece, move_opt
