# 代码块功能演示

本文档演示 md2docx 工具对代码块的支持。

## 1. 行内代码

在段落中可以使用行内代码，比如 `print()` 函数、`len()` 函数和 `range()` 函数。

使用反引号包围的文本会显示为代码样式，例如：变量 `x = 10`，函数 `calculate_sum(a, b)`。

## 2. 简单代码块

不带语言标记的代码块：

```
这是一个简单的代码块
可以包含多行文本
保持原有的缩进和格式
```

## 3. Python 代码

```python
def hello_world():
    """打印Hello World"""
    print("Hello, World!")
    return True

# 调用函数
result = hello_world()
```

## 4. JavaScript 代码

```javascript
function factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

console.log(factorial(5));  // 输出: 120
```

## 5. 带中文注释的代码

```python
# 计算斐波那契数列
def fibonacci(n):
    """
    计算第n个斐波那契数
    
    参数:
        n: 整数，表示第几个斐波那契数
    
    返回:
        整数，第n个斐波那契数
    """
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 打印前10个斐波那契数
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
```

## 6. Shell 命令示例

```bash
# 安装依赖
pip install md2docx

# 运行转换
md2docx input.md -o output.docx

# 使用自定义样式
md2docx input.md -s custom_style.yaml -o output.docx
```

## 7. 混合内容

### 列表中使用代码

常用的Python内置函数：

* `print()` - 输出函数
* `len()` - 获取长度
* `type()` - 获取类型
* `str()` - 转换为字符串
* `int()` - 转换为整数

### 表格中包含代码

| 函数 | 说明 | 示例 |
| :--- | :--- | :--- |
| `abs()` | 绝对值 | `abs(-5)` → 5 |
| `max()` | 最大值 | `max(1,2,3)` → 3 |
| `min()` | 最小值 | `min(1,2,3)` → 1 |

## 8. 多个代码块示例

第一个代码块：

```
# 配置文件
server:
  host: localhost
  port: 8080
```

第二个代码块：

```json
{
  "name": "md2docx",
  "version": "1.0.0",
  "description": "Markdown to Word converter"
}
```

第三个代码块：

```sql
SELECT id, name, age 
FROM users 
WHERE age > 18 
ORDER BY name;
```

## 9. 代码块与段落混排

在实际使用中，代码块经常与正文段落混合使用。例如，我们可以这样描述一个函数：

这个 `greet()` 函数用于问候用户：

```python
def greet(name):
    """问候函数"""
    message = f"你好，{name}！"
    print(message)
    return message
```

调用方式：`greet("张三")` 会输出 "你好，张三！"。

## 10. 空代码块

有时候可能会遇到空的代码块：

```
```

以上就是代码块功能的完整演示。

---

**测试完成**
