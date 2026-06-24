# 数学解题可视化图表设计

## 概述
在学数 bar 的解题分析中嵌入自动生成的数学图表（函数曲线、积分区域、几何图形），帮助用户通过数形结合理解题目。

## 架构

```
用户上传题目 → DeepSeek 解题分析
                  ↓
           输出文本 + 【PLOT】JSON 指令
                  ↓
           Python 渲染引擎 (matplotlib)
                  ↓
           base64 图片 → 嵌入 HTML 展示
```

## 图表类型

### 1. area — 积分区域图
用于：积分计算、曲线围成的面积
```
【PLOT】{"type":"area","curves":["x^2","x"],"x_range":[0,1],"fill":[0,1]}【/PLOT】
```
- `curves`: 曲线公式列表（按 y= 的右侧部分）
- `x_range`: x 轴显示范围
- `fill`: 填充区间 [x1, x2]
- 用不同颜色区分曲线，绿色半透明填充面积

### 2. curve — 函数曲线图
用于：函数图像、极限、导数可视化
```
【PLOT】{"type":"curve","formula":"sin(x)","x_range":[-5,5]}【/PLOT】
```
- `formula`: 单个函数表达式
- `x_range`: x 轴显示范围

### 3. multi — 多曲线对比
用于：多个函数对比、交点分析
```
【PLOT】{"type":"multi","formulas":["x^2","cos(x)","0.5"],"x_range":[-2,2]}【/PLOT】
```
- `formulas`: 多个函数表达式列表
- 自动分配颜色和图例

### 4. solid — 旋转体
用于：旋转体体积、绕轴旋转
```
【PLOT】{"type":"solid","curve":"x^2","x_range":[0,1],"axis":"x"}【/PLOT】
```
- `curve`: 被旋转的曲线
- `x_range`: 范围
- `axis`: 旋转轴 (x/y)

### 5. geometry — 几何图形
用于：圆、三角形、多边形等几何问题
```
【PLOT】{"type":"geometry","shapes":[{"type":"circle","center":[0,0],"radius":1}]}【/PLOT】
```
- `shapes`: 几何元素列表
- 支持 `circle`、`line`、`polygon`、`point` 等

## 渲染实现

- Python matplotlib，使用 SimHei 中文字体
- `plot_engine.py` — 核心渲染模块
  - `render_plot(plot_json)` → base64 PNG
  - 支持面积填充、网格线、坐标轴、图例
- 图片尺寸约 600×400px，100dpi
- 缓存：同一道题只生成一次

## 前端展示

- 解题分析中检测 `【PLOT】...【/PLOT】` 标记
- 替换为 `<img src="data:image/png;base64,...">`
- 放在解题步骤与答案之间
- 图片响应式（max-width: 100%）

## DeepSeek 集成

在解题 prompt 中加入规则：
> 如果需要画图辅助理解，在对应位置插入 `【PLOT】{JSON}【/PLOT】`

DeepSeek 根据题目类型自行判断何时插入——面积题插入 area、函数题插入 curve、几何题插入 geometry。

## 错误处理

- 渲染失败 → 不显示图片，不影响解题文本
- JSON 解析失败 → 跳过该 PLOT 块
- 未知的图表类型 → 静默忽略

## 不包含的范围

- 3D 立体旋转体渲染（先只做 2D）
- 交互式图表（鼠标悬停、缩放等）
- 动画
