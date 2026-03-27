## 1. 需要安装的第三方包

在使用此功能包之前，请确保安装以下第三方包：

- `mammoth`: 用于将 Word 文档转换为 HTML 格式。
- `html2canvas`: 用于将 HTML 内容转换为图像。
- `pdfjs-dist`: 用于解析和处理 PDF 文档。

可以通过以下命令安装这些包：

```bash
npm install mammoth html2canvas pdfjs-dist
```

## 2. 支持的文件格式

此功能包支持以下文件格式：

- `docx`: Microsoft Word 文档
- `pdf`: PDF 文档

## 3. 返回的结果

处理后的结果将返回一个对象，包含以下信息：

- `mainPages`: 主内容页的图像数据列表。
- `answerPages`: 答案页的图像数据列表。
- `scores`: 从文档中提取的分值信息数组。

## 4. 备注

- 在处理 `docx` 文档时，每一页的底部需要添加"第 X 页"以确保分页信息的正确显示。
- 答案页需要顶部标明"答案"，并且加粗

---

请根据您的需求进行相应的调整和补充。
