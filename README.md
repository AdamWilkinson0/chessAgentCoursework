# Chess Agent Coursework

The goal was to make an agent that would reliably beat the lecturers benchmark agents, which had increasing levels of difficulty. Mine beat all 5.

The game is a 5x5 version of chess with a slight variation of the pieces. Instead of rooks there's a "Right", which moves like a rook and a knight combined. Pawns can only promote to queens. Also each game has a 300 second clock shared between both players, so managing time turned out to be crucial and be the main area performance gains could be made.

The course gave us the board, rules (`extension/`) and the test harness. My work is in `agent.py`, along with a greedy opponent and some extra test boards I used to test my model against.

## How the agent works

- **Uses it's own board** - The agent copies the position into a plain 5x5 grid and generates moves
  itself. This is more efficient than cloning chessmaker boards during the search.
- **Minimax with alpha-beta pruning** - It uses iterative deepening, so there's always a best
  move ready when time runs out.
- **Transposition table** - Positions it has already searched get reused, and the best move from
  the table is tried first.
- **Quiescence search** - At the end of the search it keeps following captures, so it doesn't
  stop halfway through a trade and get the position aggresively wrong.
- **Evaluation** - It counts material, then adds bonuses for central pieces, advanced pawns and
  mobility. When it's far ahead, a "mop-up" term pushes the losing king to the edge, which
  prevented it from drawing won endgames.
- **Repetition handling** - It avoids repeating positions when it's winning but is happy to
  repeat them when losing.
- **Time management** - It's time spent thinking depends on how much of the game clock is left. It
  also won't start a new depth that likely won't finish in time.

### Running it

Needs Python 3.12 and chessmaker:

    pip install chessmaker
    python test_fullgame.py
