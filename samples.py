from chessmaker.chess.base import Player
from chessmaker.chess.pieces import King, Bishop, Knight, Queen
from extension.piece_right import Right
from extension.piece_pawn import Pawn_Q
from chessmaker.chess.base import Square

white = Player("white")
black = Player("black")

sample0 = [
        [Square(Knight(black)), Square(Queen(black)), Square(King(black)), Square(Bishop(black)), Square(Right(black))],
        [Square(Pawn_Q(black)), Square(Pawn_Q(black)), Square(Pawn_Q(black)), Square(Pawn_Q(black)),Square(Pawn_Q(black))],
        [Square(), Square(), Square(), Square(),Square()],
        [Square(Pawn_Q(white)), Square(Pawn_Q(white)), Square(Pawn_Q(white)), Square(Pawn_Q(white)),Square(Pawn_Q(white))],
        [Square(Right(white)), Square(Bishop(white)),  Square(King(white)), Square(Queen(white)), Square(Knight(white))],
        ]

sample1 = [
        [Square(Right(black)), Square(Queen(black)), Square(King(black)), Square(Knight(black)), Square(Bishop(black))],
        [Square(Pawn_Q(black)), Square(Pawn_Q(black)), Square(Pawn_Q(black)), Square(Pawn_Q(black)),Square(Pawn_Q(black))],
        [Square(), Square(), Square(), Square(),Square()],
        [Square(Pawn_Q(white)), Square(Pawn_Q(white)), Square(Pawn_Q(white)), Square(Pawn_Q(white)),Square(Pawn_Q(white))],
        [Square(Bishop(white)), Square(Knight(white)),  Square(King(white)), Square(Queen(white)), Square(Right(white))],
        ]

# my own test boards
# endgame - white has a Right and a pawn more, checking it can actually finish the game
sample2 = [
        [Square(), Square(), Square(King(black)), Square(), Square()],
        [Square(), Square(Pawn_Q(black)), Square(), Square(), Square()],
        [Square(), Square(), Square(), Square(), Square()],
        [Square(), Square(), Square(), Square(Pawn_Q(white)), Square()],
        [Square(Right(white)), Square(), Square(King(white)), Square(), Square()],
        ]

# fewer pieces, uneven sides
sample3 = [
        [Square(Bishop(black)), Square(Knight(black)), Square(King(black)), Square(Queen(black)), Square()],
        [Square(), Square(Pawn_Q(black)), Square(Pawn_Q(black)), Square(Pawn_Q(black)), Square()],
        [Square(), Square(), Square(), Square(), Square()],
        [Square(Pawn_Q(white)), Square(), Square(Pawn_Q(white)), Square(), Square(Pawn_Q(white))],
        [Square(Right(white)), Square(), Square(King(white)), Square(Knight(white)), Square()],
        ]
