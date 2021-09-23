import inspect
import typing


class Scope:
    __slots__ = ('globals', 'locals')

    def __init__(self, globals_: dict = None, locals_: dict = None):
        self.globals: dict = globals_ or {}
        self.locals: dict = locals_ or {}

    def clear_intersection(self, other_dict):
        for key, value in other_dict.items():
            if key in self.globals and self.globals[key] is value:
                del self.globals[key]
            if key in self.locals and self.locals[key] is value:
                del self.locals[key]

        return self

    def update(self, other):
        self.globals.update(other.globals)
        self.locals.update(other.locals)
        return self

    def update_globals(self, other: dict):
        self.globals.update(other)
        return self

    def update_locals(self, other: dict):
        self.locals.update(other)
        return self


def get_parent_scope_from_var(name, global_ok=False, skip_frames=0) -> typing.Optional[Scope]:
    stack = inspect.stack()
    try:
        for frame_info in stack[skip_frames + 1:]:
            frame = None

            try:
                frame = frame_info.frame

                if name in frame.f_locals or (global_ok and name in frame.f_globals):
                    return Scope(globals_=frame.f_globals, locals_=frame.f_locals)
            finally:
                del frame
    finally:
        del stack

    return None


def get_parent_var(name, global_ok=False, default=None, skip_frames=0):
    scope = get_parent_scope_from_var(name, global_ok=global_ok, skip_frames=skip_frames + 1)

    if not scope:
        return default

    if name in scope.locals:
        return scope.locals.get(name, default)

    return scope.globals.get(name, default)
