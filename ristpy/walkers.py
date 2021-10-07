import ast


class KeywordTransformer(ast.NodeTransformer):
  def visit_FunctionDef(self, node):
    return node

  def visit_AsyncFunctionDef(self, node):
    return node

  def visit_ClassDef(self, node):
    return node

  def visit_Return(self, node):
    if node.value is None:
      return node
    return ast.If(
      test=ast.NameConstant(
        value=True,
        lineno=node.lineno,
        col_offset=node.col_offset
      ),
      body=[
        ast.Expr(
          value=ast.Yield(
            value=node.value,
            lineno=node.lineno,
            col_offset=node.col_offset
          ),
          lineno=node.lineno,
          col_offset=node.col_offset
        ),
        ast.Return(
          value=None,
          lineno=node.lineno,
          col_offset=node.col_offset
        )
      ],
      orelse=[],
      lineno=node.lineno,
      col_offset=node.col_offset
    )

  def visit_Delete(self, node):
    return ast.If(
      test=ast.NameConstant(
      value=True,
      lineno=node.lineno,
      col_offset=node.col_offset
    ),
    body=[
                ast.If(
                    test=ast.Compare(
                        left=ast.Str(
                            s=target.id,
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        ),
                        ops=[
                            ast.In(
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            )
                        ],
                        comparators=[
                            self.globals_call(node)
                        ],
                        lineno=node.lineno,
                        col_offset=node.col_offset
                    ),
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=self.globals_call(node),
                                    attr='pop',
                                    ctx=ast.Load(),
                                    lineno=node.lineno,
                                    col_offset=node.col_offset
                                ),
                                args=[
                                    # 'x'
                                    ast.Str(
                                        s=target.id,
                                        lineno=node.lineno,
                                        col_offset=node.col_offset
                                    )
                                ],
                                keywords=[],
                                lineno=node.lineno,
                                col_offset=node.col_offset
                            ),
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        )
                    ],
                    orelse=[
                        # del x
                        ast.Delete(
                            targets=[target],
                            lineno=node.lineno,
                            col_offset=node.col_offset
                        )
                    ],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
                if isinstance(target, ast.Name) else
                ast.Delete(
                    targets=[target],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
                for target in node.targets
      ],
      orelse=[],
      lineno=node.lineno,
      col_offset=node.col_offset
    )

  def globals_call(self, node):
    return ast.Call(
      func=ast.Name(
        id='globals',
        ctx=ast.Load(),
        lineno=node.lineno,
        col_offset=node.col_offset
      ),
      args=[],
      keywords=[],
      lineno=node.lineno,
      col_offset=node.col_offset
    )
