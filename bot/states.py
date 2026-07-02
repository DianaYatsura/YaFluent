from aiogram.fsm.state import State, StatesGroup


class PracticeStates(StatesGroup):
    waiting_for_voice = State()


class QuizStates(StatesGroup):
    waiting_for_answer = State()
    hint_level = State()
