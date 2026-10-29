import time
import random
from extension.board_utils import list_legal_moves_for


# piece values - Right is basically a rook + knight so made it nearly a queen
pieceValues = {"P": 100, "N": 310, "B": 300, "R": 820, "Q": 900, "K": 0}

letterFor = {"Pawn": "P", "Knight": "N", "Bishop": "B", "Right": "R", "Queen": "Q", "King": "K"}

knightJumps = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
straightDirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
diagonalDirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
kingSteps = straightDirs + diagonalDirs

WIN_SCORE = 100000
SIZE = 5

# flags for transposition table entries
EXACT = 0
LOWER = 1
UPPER = 2
TABLE_LIMIT = 300000

# small bonus for being near the middle of the board
centreBonus = [
    [0, 4, 6, 4, 0],
    [4, 10, 14, 10, 4],
    [6, 14, 20, 14, 6],
    [4, 10, 14, 10, 4],
    [0, 4, 6, 4, 0],
]

# indexed by how many rows the pawn has moved up the board
pawnAdvance = [0, 8, 22, 45, 70]

positionHistory = {}
gameStart = None


class OutOfTime(Exception):
    pass


class SearchInfo:
    def __init__(self, mySide, timeLimit):
        self.mySide = mySide
        if mySide == "white":
            self.theirSide = "black"
        else:
            self.theirSide = "white"
        self.startTime = time.perf_counter()
        self.timeLimit = timeLimit
        self.nodes = 0
        self.unmovedPawns = set()
        # transposition table: position -> (depth, score, flag, best move)
        self.table = {}



def boardToGrid(board):
    grid = [["." for i in range(SIZE)] for j in range(SIZE)]
    for piece in board.get_pieces():
        pos = piece.position
        letter = letterFor.get(piece.name, "?")
        if piece.player.name == "white":
            grid[pos.y][pos.x] = letter.upper()
        else:
            grid[pos.y][pos.x] = letter.lower()
    return grid


def findUnmovedPawns(board):
    # chessmaker lets a pawn double step if it has never moved, not just from the start row
    unmoved = set()
    for piece in board.get_pieces():
        if piece.name == "Pawn":
            if getattr(piece, "_moved_turns_ago", 0) == -1:
                unmoved.add((piece.position.y, piece.position.x))
    return unmoved


def gridKey(grid, sideToMove):
    rows = []
    for row in grid:
        rows.append("".join(row))
    return "/".join(rows) + " " + sideToMove


def belongsTo(ch, side):
    if side == "white":
        return ch.isupper()
    else:
        return ch.islower()


def onBoard(y, x):
    return 0 <= y < SIZE and 0 <= x < SIZE

def otherSide(side):
    if side == "white":
        return "black"
    return "white"


def generateMoves(grid, side, info, capturesOnly=False, lastDouble=None):
    moves = []
    for y in range(SIZE):
        for x in range(SIZE):
            ch = grid[y][x]
            if ch == "." or not belongsTo(ch, side):
                continue
            kind = ch.upper()

            if kind == "P":
                if side == "white":
                    forward = -1
                else:
                    forward = 1
                newY = y + forward
                if onBoard(newY, x) and grid[newY][x] == "." and not capturesOnly:
                    moves.append((y, x, newY, x))
                    if (y, x) in info.unmovedPawns and onBoard(newY + forward, x) and grid[newY + forward][x] == ".":
                        moves.append((y, x, newY + forward, x))
                for dx in [-1, 1]:
                    if onBoard(newY, x + dx):
                        target = grid[newY][x + dx]
                        if target != "." and not belongsTo(target, side):
                            moves.append((y, x, newY, x + dx))
                        elif target == "." and lastDouble == (y, x + dx):
                            # en passant, their pawn just double stepped next to us
                            moves.append((y, x, newY, x + dx))
                continue

            jumps = []
            slides = []
            if kind == "N":
                jumps = knightJumps
            elif kind == "K":
                jumps = kingSteps
            elif kind == "B":
                slides = diagonalDirs
            elif kind == "Q":
                slides = straightDirs + diagonalDirs
            elif kind == "R":
                jumps = knightJumps
                slides = straightDirs

            for dy, dx in jumps:
                ny = y + dy
                nx = x + dx
                if onBoard(ny, nx):
                    target = grid[ny][nx]
                    if target == ".":
                        if not capturesOnly:
                            moves.append((y, x, ny, nx))
                    elif not belongsTo(target, side):
                        moves.append((y, x, ny, nx))

            for dy, dx in slides:
                ny = y + dy
                nx = x + dx
                while onBoard(ny, nx):
                    target = grid[ny][nx]
                    if target == ".":
                        if not capturesOnly:
                            moves.append((y, x, ny, nx))
                    else:
                        if not belongsTo(target, side):
                            moves.append((y, x, ny, nx))
                        break
                    ny += dy
                    nx += dx
    return moves


def makeMove(grid, move):
    # returns the new grid and where a pawn landed if it double stepped (for en passant)
    newGrid = [row[:] for row in grid]
    fy, fx, ty, tx = move
    piece = newGrid[fy][fx]
    newGrid[fy][fx] = "."
    lastDouble = None
    if piece == "P" or piece == "p":
        # pawn going diagonal onto an empty square must be en passant
        if fx != tx and grid[ty][tx] == ".":
            newGrid[fy][tx] = "."
        if abs(ty - fy) == 2:
            lastDouble = (ty, tx)
    if piece == "P" and ty == 0:
        piece = "Q"
    elif piece == "p" and ty == SIZE - 1:
        piece = "q"
    newGrid[ty][tx] = piece
    return newGrid, lastDouble


def isAttacked(grid, y, x, bySide):
    # look outwards from the square for anything of bySide that could hit it
    for dy, dx in knightJumps:
        ny = y + dy
        nx = x + dx
        if onBoard(ny, nx):
            ch = grid[ny][nx]
            if belongsTo(ch, bySide) and (ch.upper() == "N" or ch.upper() == "R"):
                return True

    for dy, dx in straightDirs:
        ny = y + dy
        nx = x + dx
        while onBoard(ny, nx):
            ch = grid[ny][nx]
            if ch != ".":
                if belongsTo(ch, bySide) and (ch.upper() == "R" or ch.upper() == "Q"):
                    return True
                break
            ny += dy
            nx += dx

    for dy, dx in diagonalDirs:
        ny = y + dy
        nx = x + dx
        while onBoard(ny, nx):
            ch = grid[ny][nx]
            if ch != ".":
                if belongsTo(ch, bySide) and (ch.upper() == "B" or ch.upper() == "Q"):
                    return True
                break
            ny += dy
            nx += dx

    for dy, dx in kingSteps:
        ny = y + dy
        nx = x + dx
        if onBoard(ny, nx) and belongsTo(grid[ny][nx], bySide) and grid[ny][nx].upper() == "K":
            return True

    # white pawns attack upwards so they sit one row below the square
    if bySide == "white":
        pawnRow = y + 1
        pawnLetter = "P"
    else:
        pawnRow = y - 1
        pawnLetter = "p"
    for dx in [-1, 1]:
        if onBoard(pawnRow, x + dx) and grid[pawnRow][x + dx] == pawnLetter:
            return True
    return False


def inCheck(grid, side):
    king = findKing(grid, side)
    if king is None:
        return True
    return isAttacked(grid, king[0], king[1], otherSide(side))


def legalMoves(grid, side, info, capturesOnly=False, lastDouble=None):
    # throw away anything that leaves our own king attacked
    moves = []
    for move in generateMoves(grid, side, info, capturesOnly, lastDouble):
        newGrid, nd = makeMove(grid, move)
        if not inCheck(newGrid, side):
            moves.append(move)
    return moves


def orderMoves(grid, moves):
    # captures first, biggest victim with the smallest attacker
    def moveScore(move):
        fy, fx, ty, tx = move
        victim = grid[ty][tx]
        attacker = grid[fy][fx]
        score = 0
        if victim != ".":
            score = 10 * pieceValues[victim.upper()] - pieceValues[attacker.upper()]
        if attacker.upper() == "P" and (ty == 0 or ty == SIZE - 1):
            score += 800
        return score
    return sorted(moves, key=moveScore, reverse=True)


def findKing(grid, side):
    target = "K"
    if side == "black":
        target = "k"
    for y in range(SIZE):
        for x in range(SIZE):
            if grid[y][x] == target:
                return (y, x)
    return None



def evaluate(grid, info):
    myScore = 0
    theirScore = 0
    myMaterial = 0
    theirMaterial = 0
    pieceCount = 0

    for y in range(SIZE):
        for x in range(SIZE):
            ch = grid[y][x]
            if ch == ".":
                continue
            pieceCount += 1
            kind = ch.upper()
            value = pieceValues[kind]

            if kind == "P":
                if ch.isupper():
                    value += pawnAdvance[SIZE - 1 - y]
                else:
                    value += pawnAdvance[y]
            elif kind == "N" or kind == "R":
                value += centreBonus[y][x]
            elif kind == "B" or kind == "Q":
                value += centreBonus[y][x] // 2

            if belongsTo(ch, info.mySide):
                myScore += value
                myMaterial += pieceValues[kind]
            else:
                theirScore += value
                theirMaterial += pieceValues[kind]

    # only kings left is a draw
    if pieceCount == 2:
        return 0

    score = myScore - theirScore

    # not checking legality here, its just a rough idea of how active the pieces are
    myMoves = len(generateMoves(grid, info.mySide, info))
    theirMoves = len(generateMoves(grid, info.theirSide, info))
    score += 3 * (myMoves - theirMoves)

    # when we are well ahead try to push their king to the edge and walk ours over
    # otherwise it just shuffles around and draws on repetition
    diff = myMaterial - theirMaterial
    if diff > 250 or diff < -250:
        myKing = findKing(grid, info.mySide)
        theirKing = findKing(grid, info.theirSide)
        if myKing is not None and theirKing is not None:
            if diff > 0:
                loser = theirKing
            else:
                loser = myKing
            edgeDist = min(loser[0], loser[1], SIZE - 1 - loser[0], SIZE - 1 - loser[1])
            kingGap = max(abs(myKing[0] - theirKing[0]), abs(myKing[1] - theirKing[1]))
            mopUp = (2 - edgeDist) * 15 + (4 - kingGap) * 6
            if diff > 0:
                score += mopUp
            else:
                score -= mopUp

    return score


def checkTime(info):
    info.nodes += 1
    if info.nodes % 200 == 0:
        if time.perf_counter() - info.startTime > info.timeLimit:
            raise OutOfTime()


def onlyKingsLeft(grid):
    count = 0
    for row in grid:
        for ch in row:
            if ch != ".":
                count += 1
    return count == 2


def quiesceMax(grid, lastDouble, alpha, beta, ply, qDepth, info):
    checkTime(info)

    # in check so standing pat isnt allowed, have to look at every way out
    if inCheck(grid, info.mySide):
        moves = legalMoves(grid, info.mySide, info, False, lastDouble)
        if len(moves) == 0:
            return -WIN_SCORE + ply
        if qDepth == 0:
            return evaluate(grid, info)
        best = -float("inf")
        for move in orderMoves(grid, moves):
            newGrid, nd = makeMove(grid, move)
            value = quiesceMin(newGrid, nd, alpha, beta, ply + 1, qDepth - 1, info)
            if value > best:
                best = value
            if best >= beta:
                return best
            if best > alpha:
                alpha = best
        return best

    standPat = evaluate(grid, info)
    if qDepth == 0:
        return standPat
    if standPat >= beta:
        return standPat
    if standPat > alpha:
        alpha = standPat

    captures = orderMoves(grid, legalMoves(grid, info.mySide, info, True, lastDouble))
    best = standPat
    for move in captures:
        newGrid, nd = makeMove(grid, move)
        value = quiesceMin(newGrid, nd, alpha, beta, ply + 1, qDepth - 1, info)
        if value > best:
            best = value
        if best >= beta:
            return best
        if best > alpha:
            alpha = best
    return best

def quiesceMin(grid, lastDouble, alpha, beta, ply, qDepth, info):
    checkTime(info)

    if inCheck(grid, info.theirSide):
        moves = legalMoves(grid, info.theirSide, info, False, lastDouble)
        if len(moves) == 0:
            return WIN_SCORE - ply
        if qDepth == 0:
            return evaluate(grid, info)
        best = float("inf")
        for move in orderMoves(grid, moves):
            newGrid, nd = makeMove(grid, move)
            value = quiesceMax(newGrid, nd, alpha, beta, ply + 1, qDepth - 1, info)
            if value < best:
                best = value
            if best <= alpha:
                return best
            if best < beta:
                beta = best
        return best

    standPat = evaluate(grid, info)
    if qDepth == 0:
        return standPat
    if standPat <= alpha:
        return standPat
    if standPat < beta:
        beta = standPat

    captures = orderMoves(grid, legalMoves(grid, info.theirSide, info, True, lastDouble))
    best = standPat
    for move in captures:
        newGrid, nd = makeMove(grid, move)
        value = quiesceMax(newGrid, nd, alpha, beta, ply + 1, qDepth - 1, info)
        if value < best:
            best = value
        if best <= alpha:
            return best
        if best < beta:
            beta = best
    return best


def tableKey(grid, side, lastDouble):
    # en passant square matters too, same board can have different moves
    return gridKey(grid, side) + " " + str(lastDouble)


def scoreToTable(score, ply):
    # mate scores depend on ply, store them as distance from this node instead
    if score > WIN_SCORE - 1000:
        return score + ply
    if score < -WIN_SCORE + 1000:
        return score - ply
    return score


def scoreFromTable(score, ply):
    if score > WIN_SCORE - 1000:
        return score - ply
    if score < -WIN_SCORE + 1000:
        return score + ply
    return score


def probeTable(key, depth, alpha, beta, ply, info):
    # returns (score or None, best move from before)
    entry = info.table.get(key)
    if entry is None:
        return None, None
    entryDepth, score, flag, bestMove = entry
    if entryDepth >= depth:
        score = scoreFromTable(score, ply)
        if flag == EXACT:
            return score, bestMove
        if flag == LOWER and score >= beta:
            return score, bestMove
        if flag == UPPER and score <= alpha:
            return score, bestMove
    return None, bestMove


def storeTable(key, depth, value, alphaStart, beta, bestMove, ply, info):
    if len(info.table) >= TABLE_LIMIT and key not in info.table:
        return
    if value <= alphaStart:
        flag = UPPER
    elif value >= beta:
        flag = LOWER
    else:
        flag = EXACT
    info.table[key] = (depth, scoreToTable(value, ply), flag, bestMove)


def tableMoveFirst(grid, moves, tableMove):
    # best move from the table goes first, then the usual capture ordering
    ordered = orderMoves(grid, moves)
    if tableMove is not None and tableMove in ordered:
        ordered.remove(tableMove)
        ordered.insert(0, tableMove)
    return ordered


def maxValue(grid, lastDouble, depth, alpha, beta, ply, info):
    checkTime(info)
    key = tableKey(grid, info.mySide, lastDouble)
    if depth > 0:
        stored, tableMove = probeTable(key, depth, alpha, beta, ply, info)
        if stored is not None:
            return stored
    else:
        tableMove = None
    moves = legalMoves(grid, info.mySide, info, False, lastDouble)
    # no legal moves is checkmate or stalemate, both lose in this game
    # (checked before depth 0 so mates right on the horizon still count)
    if len(moves) == 0:
        return -WIN_SCORE + ply
    if onlyKingsLeft(grid):
        return 0
    if depth == 0:
        return quiesceMax(grid, lastDouble, alpha, beta, ply, 4, info)

    alphaStart = alpha
    value = -float("inf")
    bestMove = None
    for move in tableMoveFirst(grid, moves, tableMove):
        newGrid, nd = makeMove(grid, move)
        score = minValue(newGrid, nd, depth - 1, alpha, beta, ply + 1, info)
        if score > value:
            value = score
            bestMove = move
        if value >= beta:
            break
        alpha = max(alpha, value)
    storeTable(key, depth, value, alphaStart, beta, bestMove, ply, info)
    return value


def minValue(grid, lastDouble, depth, alpha, beta, ply, info):
    checkTime(info)
    key = tableKey(grid, info.theirSide, lastDouble)
    if depth > 0:
        stored, tableMove = probeTable(key, depth, alpha, beta, ply, info)
        if stored is not None:
            return stored
    else:
        tableMove = None
    moves = legalMoves(grid, info.theirSide, info, False, lastDouble)
    if len(moves) == 0:
        return WIN_SCORE - ply
    if onlyKingsLeft(grid):
        return 0
    if depth == 0:
        return quiesceMin(grid, lastDouble, alpha, beta, ply, 4, info)

    betaStart = beta
    value = float("inf")
    bestMove = None
    for move in tableMoveFirst(grid, moves, tableMove):
        newGrid, nd = makeMove(grid, move)
        score = maxValue(newGrid, nd, depth - 1, alpha, beta, ply + 1, info)
        if score < value:
            value = score
            bestMove = move
        if value <= alpha:
            break
        beta = min(beta, value)
    storeTable(key, depth, value, alpha, betaStart, bestMove, ply, info)
    return value


def repetitionPenalty(childGrid, info, currentEval):
    key = gridKey(childGrid, info.theirSide)
    seen = positionHistory.get(key, 0)
    if seen == 0:
        return 0
    # if we're winning we don't want a draw, if losing a draw is fine
    if currentEval > 50:
        return -60 * seen
    elif currentEval < -150:
        return 30 * seen
    return -10 * seen


def agent(board, player, var):
    """"
    Parameters
    ----------
    board: the current chess board
    player: your assigned player role (white or black)
    var:  [ply, THINKING_TIME_BUDGET] a list cotaining the ply ID and the thinking_time_budget (secs)

    Returns
    -------
    piece: your selected chess piece
    move_opt: your selected move of your selected chess piece
    """
    piece, move_opt = None, None

    legal = list_legal_moves_for(board, player)
    if len(legal) == 0:
        return piece, move_opt
    piece, move_opt = legal[0]
    if len(legal) == 1:
        return piece, move_opt

    global gameStart
    # new game so reset stuff
    if var[0] <= 2 or gameStart is None:
        gameStart = time.perf_counter()
        positionHistory.clear()

    # whole game is only 300s shared between both of us so dont use the full 14s,
    # leave a safety margin and think less as the game clock runs down
    thinkingBudget = var[1]
    gameUsed = time.perf_counter() - gameStart
    timeLeft = 300 - gameUsed
    timeLimit = min(thinkingBudget * 0.6, timeLeft / 15)
    if timeLimit < 0.3:
        timeLimit = 0.3
    info = SearchInfo(player.name, timeLimit)

    try:
        grid = boardToGrid(board)
        info.unmovedPawns = findUnmovedPawns(board)
        myKey = gridKey(grid, info.mySide)
        positionHistory[myKey] = positionHistory.get(myKey, 0) + 1

        rootMoves = []
        for pc, opt in legal:
            fromPos = pc.position
            toPos = opt.position
            gridMove = (fromPos.y, fromPos.x, toPos.y, toPos.x)
            childGrid, childDouble = makeMove(grid, gridMove)
            rootMoves.append([pc, opt, childGrid, childDouble, 0])

        currentEval = evaluate(grid, info)
        penalties = []
        for rm in rootMoves:
            penalties.append(repetitionPenalty(rm[2], info, currentEval))

        bestIndex = 0
        depth = 1
        while depth <= 30:
            alpha = -float("inf")
            depthBest = None
            depthBestScore = -float("inf")
            try:
                # search the moves that looked good last time first
                order = sorted(range(len(rootMoves)), key=lambda i: rootMoves[i][4], reverse=True)
                for i in order:
                    score = minValue(rootMoves[i][2], rootMoves[i][3], depth - 1, alpha, float("inf"), 1, info)
                    score += penalties[i]
                    rootMoves[i][4] = score
                    if score > depthBestScore:
                        depthBestScore = score
                        depthBest = i
                    if score > alpha:
                        alpha = score
            except OutOfTime:
                break

            bestIndex = depthBest
            print(f"Ply {var[0]}: depth {depth} best score {depthBestScore} nodes {info.nodes}")
            # found a forced win (or every move loses) so no point going deeper
            if depthBestScore > WIN_SCORE - 100 or depthBestScore < -WIN_SCORE + 100:
                break
            # next depth takes a few times longer, if over half the time is gone it
            # probably wont finish so save the game clock instead
            if time.perf_counter() - info.startTime > timeLimit * 0.5:
                break
            depth += 1

        piece = rootMoves[bestIndex][0]
        move_opt = rootMoves[bestIndex][1]

        childKey = gridKey(rootMoves[bestIndex][2], info.theirSide)
        positionHistory[childKey] = positionHistory.get(childKey, 0) + 1

    except Exception as e:
        print("agent error:", e)
        piece, move_opt = random.choice(legal)

    return piece, move_opt
