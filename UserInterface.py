import pygame
import chess

UNICODE_PIECES = {
    "P": "\u2659",
    "N": "\u2658",
    "B": "\u2657",
    "R": "\u2656",
    "Q": "\u2655",
    "K": "\u2654",
    "p": "\u265f",
    "n": "\u265e",
    "b": "\u265d",
    "r": "\u265c",
    "q": "\u265b",
    "k": "\u265a",
}


class UserInterface:
    def __init__(self, surface, board):
        self.surface = surface
        self.board = board
        self.square_size = surface.get_width() // 8
        self.selected_square = None
        self.last_move = None
        self.valid_moves = []
        self.playerColor = chess.WHITE
        self.allow_both_colors = True
        self.white_time = 300
        self.black_time = 300
        self.game_result_text = ""

        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.SELECTED_COLOR = (130, 151, 105)
        self.VALID_MOVE_COLOR = (186, 202, 43)
        self.LAST_MOVE_COLOR = (205, 210, 106)
        self.TEXT_COLOR = (0, 0, 0)

        pygame.font.init()
        self.info_font = pygame.font.Font(None, 30)
        self.piece_font = pygame.font.Font(None, int(self.square_size * 0.8))

    def _screen_coords(self, file_idx, rank_idx):
        x = file_idx * self.square_size
        if self.playerColor == chess.WHITE:
            y = (7 - rank_idx) * self.square_size
        else:
            y = rank_idx * self.square_size
        return x, y

    def get_square_from_pos(self, pos):
        x, y = pos
        if not (0 <= x < self.surface.get_width() and 0 <= y < self.surface.get_height()):
            return None
        file_idx = x // self.square_size
        if self.playerColor == chess.WHITE:
            rank_idx = 7 - (y // self.square_size)
        else:
            rank_idx = y // self.square_size
        if 0 <= file_idx <= 7 and 0 <= rank_idx <= 7:
            return chess.square(file_idx, rank_idx)
        return None

    def drawComponent(self):
        self.surface.fill((255, 255, 255))
        for rank_idx in range(8):
            for file_idx in range(8):
                square = chess.square(file_idx, rank_idx)
                x, y = self._screen_coords(file_idx, rank_idx)
                color = self.LIGHT_SQUARE if (file_idx + rank_idx) % 2 == 0 else self.DARK_SQUARE

                if square == self.selected_square:
                    color = self.SELECTED_COLOR
                elif self.last_move and (
                    chess.square_name(square) == self.last_move[:2]
                    or chess.square_name(square) == self.last_move[2:4]
                ):
                    color = self.LAST_MOVE_COLOR
                elif any(chess.square_name(square) == move[2:4] for move in self.valid_moves):
                    color = self.VALID_MOVE_COLOR

                pygame.draw.rect(
                    self.surface, color, (x, y, self.square_size, self.square_size)
                )

                piece = self.board.board.piece_at(square)
                if piece:
                    text = UNICODE_PIECES[piece.symbol()]
                    color_text = (20, 20, 20) if piece.color == chess.BLACK else (245, 245, 245)
                    glyph = self.piece_font.render(text, True, color_text)
                    rect = glyph.get_rect(
                        center=(x + self.square_size // 2, y + self.square_size // 2)
                    )
                    self.surface.blit(glyph, rect)

        white_minutes = int(self.white_time // 60)
        white_seconds = int(self.white_time % 60)
        black_minutes = int(self.black_time // 60)
        black_seconds = int(self.black_time % 60)
        turn = "White" if self.board.board.turn == chess.WHITE else "Black"

        info_top = f"Turn: {turn}   White: {white_minutes:02d}:{white_seconds:02d}   Black: {black_minutes:02d}:{black_seconds:02d}"
        top_text = self.info_font.render(info_top, True, self.TEXT_COLOR)
        self.surface.blit(top_text, (8, 8))

        if self.game_result_text:
            result_surface = self.info_font.render(self.game_result_text, True, (190, 30, 30))
            self.surface.blit(result_surface, (8, self.surface.get_height() - 30))

        pygame.display.flip()

    def show_game_over_message(self, result_text):
        self.game_result_text = result_text
        self.drawComponent()

    def _promotion_suffix(self, move_prefix):
        """Prefer queen promotion, fallback to any legal promotion."""
        legal = self.board.get_legal_moves()
        candidates = [m for m in legal if m.startswith(move_prefix)]
        if not candidates:
            return None
        for suffix in ("q", "r", "b", "n"):
            if f"{move_prefix}{suffix}" in candidates:
                return suffix
        if len(candidates[0]) == 5:
            return candidates[0][4]
        return ""

    def handle_click(self, pos):
        if self.board.is_game_over():
            return None

        square = self.get_square_from_pos(pos)
        if square is None:
            return None

        current_turn = self.board.board.turn
        if not self.allow_both_colors and self.playerColor is not None and current_turn != self.playerColor:
            return None

        if self.selected_square is None:
            piece = self.board.board.piece_at(square)
            if piece and piece.color == current_turn:
                self.selected_square = square
                self.valid_moves = [
                    move
                    for move in self.board.get_legal_moves()
                    if chess.square_name(square) == move[:2]
                ]
            return None

        move_prefix = chess.square_name(self.selected_square) + chess.square_name(square)
        self.selected_square = None
        self.valid_moves = []

        legal_moves = self.board.get_legal_moves()
        if move_prefix in legal_moves:
            return move_prefix

        promo = self._promotion_suffix(move_prefix)
        if promo is None:
            return None
        return f"{move_prefix}{promo}" if promo else move_prefix