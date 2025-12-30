# 📖 RIST Language Reference Guide (Final)

## 📄 `README.md`

RIST (Reduced Instruction Set Text) is a concise, "Short Text Python" language designed to minimize keystrokes while maintaining high readability and direct transpilation to standard Python 3.

---

## 🚀 I. Core Design Philosophy

RIST introduces C-style syntax features to replace verbose Python keywords and mandatory indentation.

* **Target:** `Python 3.x`
* **Compilation:** RIST code is transpiled 1:1 into valid, runnable Python code.
* **Code Blocks:** Code blocks can be defined using **curly braces (`{}`)** instead of mandatory indentation.
* **Separators:** Semicolons (`;`) can optionally be used as statement separators.

---

## II. Syntax Shortcuts

### A. Imports

| Feature | RIST Syntax | Python Equivalent |
| :--- | :--- | :--- |
| **Standard Import** | `@+ module_name` | `import module_name` |
| **`from ... import *`** | `@+ module_name` | `from module_name import *` |
| **Alias Import** | `@+ module as alias` | `import module as alias` |

**Example Code:**

```rist
@+ sys; @+ pandas as pd
@+ my_utils 
```

### B. Function and Class Definitions

RIST uses a trailing operator to define functions.

| Feature | RIST Syntax | Python Equivalent |
| :--- | :--- | :--- |
| **Synchronous Function** | `func$() { ... }` | `def func(): ...` |
| **Asynchronous Function** | `$func$() { ... }` | `async def func(): ...` |
| **Class Definition** | `class name { ... }` | `class name: ...` |
| **Inline Function (Closure)** | `(args) => { return expr; }` | (Feature Under Development) |

**Example Code:**

```rist
class APIClient {
    init$(self, url) {
        self.url = url;
    }
}

$async_fetch$() {
    # ...
}
```

---

## III. Flow Control Operators (With Constraints)

### A. Range Operator (`..`)

The RIST Range Operator provides a concise way to define iterable ranges. It transpiles to Python's exclusive-end `range(start, end)`.

| RIST Syntax | Python Equivalent |
| :--- | :--- |
| `(start)..(end)` | `range(start, end)` |

#### ⚠️ **Constraint: Range Operands Parentheses**

If the start or end operand is a variable or a complex expression, **both operands MUST be wrapped in parentheses** to enforce parser boundaries and avoid `SyntaxError`.

**Example Code:**

```rist
MAX_VAL = 10;
for i in 1..(MAX_VAL) {
    # Prints 1, 2, ..., 9
    print(i)
}

start_num = 5
end_num = start_num + 3
for x in (start_num)..(end_num):
    # Prints 5, 6, 7
    print(x)
```

### B. Ternary Conditional Operator (`? :`)

The short, standard conditional operator.

| RIST Syntax | Python Equivalent |
| :--- | :--- |
| **`(condition) ? true_val : false_val`** | `true_val if condition else false_val` |

#### ⚠️ **Constraint 1: Condition Parentheses**

The `condition` part of the ternary operator **MUST be enclosed in parentheses** (e.g., `(a > b)`) to ensure correct parsing.

#### ⚠️ **Constraint 2: Single-Line Requirement**

The entire ternary expression **MUST be written on a single line** to avoid `IndentationError` when parsing the `?` and `:` symbols.

**Example Code:**

```rist
age = 25;
status = (age >= 18) ? "Adult" : "Minor"; 
# status == "Adult"

mode = (is_debug) ? "DEV" : ((is_prod) ? "PROD" : "TEST"); 
# Example of a valid, single-line nested ternary
```

---

## IV. Scope and Closures

### 🚧 **Inline Function Scope (Feature Under Development)**

The inline function syntax (``(args) => { ... }``) is currently under development to ensure reliable scope resolution (closures) in all scenarios.

**General Guidance:**

We recommend relying on **Global** variables or **Function Arguments** for any variables used within an inline function's body until this feature reaches stability.

**Example Code (Demonstrating Target Intent):**

```rist
BASE_FACTOR = 5; # GLOBAL variable

main_test$(input_val) { # input_val is a function ARGUMENT
    processor = (x) => {
        # This will be the intended stable usage:
        return (x * BASE_FACTOR) + input_val;
    }
}
```
