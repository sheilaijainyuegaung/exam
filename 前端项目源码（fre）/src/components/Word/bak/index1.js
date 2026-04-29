/* eslint-disable */
import mammoth from 'mammoth'
import html2canvas from 'html2canvas'
//import * as pdfjsLib from 'pdfjs-dist'
// 设置 PDF.js worker 路径
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`

const chineseNoRegs = [/一、/, /二、/, /三、/, /四、/, /五、/, /六、/, /七、/, /八、/, /九、/, /十、/, /十一、/, /十二、/, /十三、/, /十四、/, /十五、/, /十六、/, /十七、/, /十八、/, /十九、/, /二十、/]

/**
 * 从PDF页面中提取标题
 * @param {Object} pageTextContent - PDF页面的文本内容对象
 * @returns {string} 提取到的标题
 */
const extractPdfTitle = (pageTextContent) => {
  // 提取并处理页面文本
  const lines = pageTextContent.items.reduce((acc, item) => {
    // 如果当前项与上一项的y坐标接近，认为是同一行
    const lastLine = acc[acc.length - 1]
    if (lastLine && Math.abs(lastLine.y - item.transform[5]) < 5) {
      lastLine.text += item.str
    } else {
      acc.push({
        text: item.str,
        y: item.transform[5],
        fontSize: item.transform[0] // 字体大小通常存储在transform矩阵的第一个元素
      })
    }
    return acc
  }, [])

  // 按y坐标从上到下排序
  lines.sort((a, b) => b.y - a.y)

  // 标题特征匹配
  const titlePatterns = [
    /.*[试卷试题测试考试]$/,
    /.*[试卷试题测试考试][（(].+[)）]/,
    /^20\d{2}年?.+[试卷试题测试考试]/,
    /.*[年级学科科目].+[试卷试题测试考试]/,
    /.*[单元月中期末]考.*/
  ]

  let title = ''

  // 查找符合标题特征的文本
  for (const line of lines) {
    const text = line.text.trim()
    // 检查文本长度是否在合理范围内
    if (text.length >= 10 && text.length <= 50) {
      // 检查是否匹配标题模式
      if (titlePatterns.some(pattern => pattern.test(text))) {
        title = text
        break
      }
    }
  }
  // 如果没有找到符合特征的标题，使用第一行文本（长度合适的）
  if (!title) {
    for (const line of lines) {
      const text = line.text.trim()
      if (text.length >= 3 && text.length <= 50) {
        title = text
        break
      }
    }
  }

  return title
}

/**
 * 从PDF页面文本内容中提取行
 * @param {Object} pageTextContent - PDF页面的文本内容对象
 * @returns {Array<string>} 提取到的行文本数组
 */
const extractLinesFromPdfPage = (pageTextContent) => {
  if (!pageTextContent || !pageTextContent.items) return [];

  const linesData = pageTextContent.items.reduce((acc, item) => {
    const lastLine = acc[acc.length - 1];
    // 阈值可以根据实际情况调整，用于判断是否为同一行
    if (lastLine && Math.abs(lastLine.y - item.transform[5]) < 5) {
      lastLine.text += item.str;
    } else {
      acc.push({
        text: item.str,
        y: item.transform[5],
      });
    }
    return acc;
  }, []);

  // 按y坐标从上到下排序（PDF坐标系通常y轴向下为正）
  // 如果是从上到下渲染，应该是 linesData.sort((a, b) => a.y - b.y);
  // 但你之前的 extractPdfTitle 是 b.y - a.y，这里保持一致，如果后续发现顺序不对再调整
  linesData.sort((a, b) => b.y - a.y);
  return linesData.map(line => line.text);
};

export const fileChangeHandler = async (file) => {
  if (!file) return

  const isValidFormat = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ].includes(file.raw.type)
  if (!isValidFormat) {
    throw new Error('Invalid file format')
  }

  let res = null
  if (file.raw.type.includes('pdf')) {
    res = await handlePdfDocument(file.raw)
  } else {
    res = await handleWordDocument(file.raw)
  }
  return res
}
function splitOnce(str, separator) {
  const index = str.indexOf(separator);
  if (index === -1) return [str];
  return [
    str.substring(0, index),
    str.substring(index + separator.length)
  ];
}
/**
 * 从HTML内容中提取分值信息
 * @param {string} htmlContent - 需要处理的HTML内容
 * @returns {Array} 返回提取的分值信息数组
 */
export function extractScores(htmlContent, title) {

  // 定义标题匹配模式
  const maxLevel = 3

  // 分值提取正则（全局匹配）
  const scorePattern = /[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/g;
  const singleScorePattern = /[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/;

  // 移除所有图片标签和空白字符
  let contentWithoutImages = htmlContent.replace(/<img[^>]*>/g, '').replace(/（/g, '(').replace(/）/g, ')').replace(/\s+/g, '').trim()
  if (title) {
    contentWithoutImages = contentWithoutImages.split(title.replace(/\s+/g, '').replace(/（/g, '(').replace(/）/g, ')').trim())[1]
  }
  // 判断试卷是什么类型
  const templateType = getTemplateType(contentWithoutImages);

  // 构建文本树
  const textTree = processText(contentWithoutImages);

  // 提取分值信息
  const scoresList = extractScoreInfo(textTree);

  const treeDepth = getTreeDepth(scoresList);
  const questionType = getQuestionType(templateType, treeDepth);

  // 递归处理文本，构建树结构
  function processText(text, level = 0, prevCounter = 0) {
    if (!text || text.length === 0) return null;

    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {
      // 查找所有分值
      const scores = Array.from(text.matchAll(scorePattern))
        .map(match => parseFloat(match[1]));

      // 如果有多个分值，创建子节点
      if (scores.length > 1) {
        return {
          text: text,
          score: scores.reduce((a, b) => a + b, 0),
          childText: scores.map(score => ({
            text: `(${score}分)`,
            score: score,
            childText: []
          }))
        };
      } else {
        // 单个分值的情况
        const scoreMatch = text.match(singleScorePattern);
        const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;
        // 如果分值为0，返回null
        return score > 0 ? {
          text: text,
          score: score,
          childText: []
        } : null;
      }
    }

    let segments = [];
    let tempText = text;

    // 根据不同的模式类型使用不同的匹配逻辑
    if (level === 0) { // 中文数字标题
      // 按照 chineseNoRegs 数组顺序尝试匹配
      for (let i = 0; i < chineseNoRegs.length; i++) {
        const pattern = chineseNoRegs[i];
        const match = tempText.match(pattern);
        if (!match) {
          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
        const [first, rest] = splitOnce(tempText, match[0]);
        segments.push(first);
        tempText = rest;
      }
    } else { // 阿拉伯数字标题或括号数字标题
      let counter = templateType !== '4' ? 1 : prevCounter + 1;

      while (true) {
        let pattern;
        if (level === 1) {
          // 当type是pdf时从头部开始匹配
          pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．]`);
        } else {
          pattern = new RegExp(`\\(${counter}\\)`);
        }
        const match = tempText.match(pattern);
        if (!match) {
          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
        const [first, rest] = splitOnce(tempText, match[0]);
        segments.push(first);
        tempText = rest;
        counter++;
      }
    }
    // 处理分割后的文本段
    const result = [];
    const counterSeries = []

    for (let i = 1; i < segments.length; i++) {
      const segment = segments[i].trim();
      if (segment) {
        const node = processText(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
        if (node) {
          counterSeries.push(node.length)
          result.push(node);
        }
      }
    }

    // 如果没有有效的子节点，尝试下一级模式
    if (result.length === 0) {
      return processText(text, level + 1);
    }

    return result;
  }

  // 提取分值信息
  function extractScoreInfo(node, parent = null, grandParent = null, siblings = [], parentSiblings = []) {
    if (!node) return null;

    // 如果是数组（多个同级节点）
    if (Array.isArray(node)) {
      const validNodes = node.map((item, index) =>
        extractScoreInfo(
          item,
          null,
          null,
          node.slice(0, index), // 传递当前节点之前的兄弟节点
          []
        )
      ).filter(Boolean);

      if (validNodes.length === 0) return null;

      // 计算总分并构建新的结构
      const totalScore = validNodes.reduce((sum, item) => sum + item.score, 0);
      return {
        score: totalScore,
        childScores: validNodes
      };
    }
    // 处理子节点的分值
    const childScores = node.childText.length > 0
      ? node.childText.map((child, index) =>
        extractScoreInfo(
          child,
          node,
          parent,
          node.childText.slice(0, index),
          siblings
        )
      ).filter(Boolean)
      : [];

    // 如果当前节点分值为0且没有有效的子节点分值，返回null
    if (node.score === 0 && childScores.length === 0) {
      return null;
    }

    let currentScore = node.score;
    let finalChildScores = childScores;

    // 新增的逻辑：处理 childScores，只考虑长度大于2的数组
    if (finalChildScores.length > 1) {
      const firstScore = finalChildScores[0].score;
      const remainingSum = finalChildScores.slice(1).reduce((sum, item) => sum + item.score, 0);

      if (finalChildScores.length > 2 && firstScore === remainingSum) {
        // 情况1：第一项等于后面所有项之和
        return {
          score: firstScore,
          childScores: finalChildScores.slice(1)
        };
      } else {
        // 情况2：第一项不等于后面所有项之和
        return {
          score: finalChildScores.reduce((sum, item) => sum + item.score, 0),
          childScores: finalChildScores
        };
      }
    }

    // 如果有子节点，使用子节点分数之和
    if (finalChildScores.length > 0) {
      currentScore = finalChildScores.reduce((sum, item) => sum + item.score, 0);
    }

    return {
      score: currentScore,
      childScores: finalChildScores.length > 0 ? finalChildScores : undefined
    };
  }

  // 判断试卷是什么类型
  function getTemplateType(text) {
    let hasChineseNo = false;
    let hasArabicNo = false;
    let arabicNumbers = [];
    let tempText = text;
    let segments = [];

    // 检查中文数字标题
    for (let i = 0; i < chineseNoRegs.length; i++) {
      const pattern = chineseNoRegs[i];
      const match = tempText.match(pattern);
      if (!match) {
        segments.push(tempText);
        break;
      }
      if (i === 0) hasChineseNo = true;
      const [first, rest] = splitOnce(tempText, match[0]);
      tempText = rest;
      segments.push(first);
    }

    // 检查阿拉伯数字标题
    tempText = text;

    segments.forEach(segment => {
      let counter = arabicNumbers.length > 0 ? arabicNumbers[arabicNumbers.length - 1] + 1 : 1;
      while (true) {
        let pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．]`);
        let match = segment.match(pattern);
        if (!match) {
          counter = 1;
          pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．]`);
          match = segment.match(pattern);
          if (!match) break;
        }
        if (counter === 1) hasArabicNo = true;
        arabicNumbers.push(counter);
        const [first, rest] = splitOnce(segment, match[0]);
        segment = rest;
        counter++;
      }
    });

    // 如果没有匹配项，返回 null
    if (!hasChineseNo && !hasArabicNo) {
      return null;
    }

    // 情况1：只有中文数字标题
    if (hasChineseNo && !hasArabicNo) {
      return '1';
    }

    // 情况2：只有阿拉伯数字标题
    if (!hasChineseNo && hasArabicNo) {
      return '2';
    }

    // 如果同时存在中文和阿拉伯数字标题
    if (hasChineseNo && hasArabicNo) {
      // 检查数字是否连续
      const isSequential = arabicNumbers.every((num, index) => {
        if (index === 0) return true;
        return num === arabicNumbers[index - 1] + 1;
      });

      // 情况3和4：根据阿拉伯数字是否连续返回不同类型
      return isSequential ? '4' : '3';
    }

    return null;
  }

  return {
    scoresList,
    questionType,
  };

}
export const processHtmlContent = async (htmlContent) => {
  try {
    const mainPagesList = []
    const answerPagesList = []

    // 获取试卷标题，第一个strong标签包裹的内容
    const title = htmlContent.match(/<strong>(.*?)<\/strong>/)[1]

    // 将em标签中间的空格替换为_
    const processedContent = htmlContent
      .replace(/<em>([^<]*)<\/em>/g, (match, p1) => `${p1.replace(/\s+/g, (space) => '_'.repeat(space.length))}`)
      .replace(/（/g, '(').replace(/）/g, ')')

    const splitContent = processedContent.split(
      /<p><strong>答案<\/strong><\/p>/
    )
    const mainContent = splitContent[0]
    const answerContent = splitContent[1]
      ? `<p><strong>答案</strong></p>${splitContent[1]}`
      : ''

    const { scoresList, questionType } = extractScores(mainContent.replace(title, ''))


    const pageRegex = /第[一二三四五六七八九十]+页|第\d+页/g
    const isValidPage = (page) => page.trim().length > 0 && page !== '<p>' && page !== '</p>' && page !== '<p></p>';
    const filterValidPages = (pages) => pages.filter(isValidPage);

    const validPages = filterValidPages(mainContent.split(pageRegex));
    const validAnswerPages = answerContent ? filterValidPages(answerContent.split(pageRegex)) : [];

    const container = document.createElement('div')
    container.style.position = 'absolute'
    container.style.left = '-9999px'
    container.style.top = '0'

    const pageStyle = `
      <style>
        .virtual-page {
          width: 210mm;
          min-height: 297mm;
          padding: 12mm;
          margin-bottom: 20px;
          background: white;
          box-shadow: 0 0 5px rgba(0,0,0,0.1);
          box-sizing: border-box;
          position: relative;
          overflow: hidden;
          page-break-after: always;
        }
        .virtual-page-content {
          font-size: 16pt;
          line-height: 1.5;
        }
        .document-footer {
          position: absolute;
          bottom: 20mm;
          left: 20mm;
          right: 20mm;
          text-align: center;
          font-size: 10pt;
          color: #666;
        }
        .answer-page {
          border-top: 2px solid #333;
          margin-top: 20px;
          padding-top: 20px;
        }
      </style>
    `

    container.innerHTML =
      pageStyle +
      validPages
        .map(
          (content, index) => `
      <div class="virtual-page" id="page-${index + 1}">
        <div class="virtual-page-content">
          ${content}
        </div>
      </div>
    `
        )
        .join('') +
      validAnswerPages
        .map(
          (content, index) => `
      <div class="virtual-page answer-page" id="answer-page-${index + 1}">
        <div class="virtual-page-content">
          ${content}
        </div>
        <div class="document-footer">
          答案第 ${index + 1} 页
        </div>
      </div>
    `
        )
        .join('')

    document.body.appendChild(container)

    const totalPagesCount = validPages.length
    for (let i = 0; i < totalPagesCount; i++) {
      const pageElement = container.querySelector(`#page-${i + 1}`)
      const canvas = await html2canvas(pageElement, {
        scale: 4,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      })

      mainPagesList.push(canvas.toDataURL('image/jpeg', 0.9))
    }

    const totalAnswerPages = validAnswerPages.length
    for (let i = 0; i < totalAnswerPages; i++) {
      const pageElement = container.querySelector(`#answer-page-${i + 1}`)
      const canvas = await html2canvas(pageElement, {
        scale: 4,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      })

      answerPagesList.push(canvas.toDataURL('image/jpeg', 0.9))
    }

    document.body.removeChild(container)

    return {
      mainPages: mainPagesList,
      answerPages: answerPagesList,
      scores: scoresList,
      questionType,
      title
    }
  } catch (error) {
    throw new Error('HTML内容处理失败：' + error.message)
  }
}
export const handleWordDocument = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const options = {
      styleMap: [
        "u => em",
      ],
    }

    const result = await mammoth.convertToHtml({ arrayBuffer }, options)

    return await processHtmlContent(result.value)
  } catch (error) {
    throw new Error('Word文档处理失败：' + error.message)
  }
}
export const handlePdfDocument = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    const totalPages = pdf.numPages

    let answerStartPage = null
    let htmlContent = ''
    const mainPages = []
    const answerPages = []
    let allLines = []; // 用于存储所有非答案页的行

    // 获取第一页内容并提取标题
    const firstPage = await pdf.getPage(1)

    const firstPageText = await firstPage.getTextContent()
    const title = extractPdfTitle(firstPageText)

    for (let i = 1; i <= totalPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items.map(item => item.str).join(' ')

      const answerPattern = /(^|\s|[。．.、\n])(参考)?答案($|\s|[：:．.、\n])/g
      if (answerPattern.test(pageText) && !answerStartPage) {
        answerStartPage = i
      }

      const viewport = page.getViewport({ scale: 2.0 })
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      canvas.height = viewport.height
      canvas.width = viewport.width

      await page.render({
        canvasContext: context,
        viewport: viewport
      }).promise

      const imageUrl = canvas.toDataURL('image/jpeg', 0.9)
      if (answerStartPage && i >= answerStartPage) {
        answerPages.push(imageUrl)
      } else {
        // 使用新函数提取行，并添加到 allLines 数组
        const linesFromPage = extractLinesFromPdfPage(textContent);
        allLines = allLines.concat(linesFromPage);
        mainPages.push(imageUrl)
      }

      canvas.remove()
    }

    // 将所有行合并为一个字符串，用换行符分隔，每一行头部添加<p>
    htmlContent = allLines.map(line => `<p>${line}</p>`).join('');

    const { scoresList, questionType } = extractScores(htmlContent, title)
    return {
      mainPages,
      answerPages,
      scores: scoresList,
      questionType,
      title
    }

  } catch (error) {
    throw new Error('PDF文档处理失败：' + error.message)
  }
}

function getTreeDepth(node) {
  if (!node || !node.childScores) return 0;
  let maxDepth = 0;
  for (const child of node.childScores) {
    const childDepth = getTreeDepth(child);
    if (childDepth > maxDepth) {
      maxDepth = childDepth;
    }
  }
  return maxDepth + 1;
}

function getQuestionType(templateType, treeDepth) {
  let tt = `${templateType},${treeDepth}`
  if (tt[0] === '2' && tt[2] > 2) {
    tt = '2,2'
  }
  if ((tt[0] === '3' || tt[0] === '4') && tt[2] > 3) {
    tt = '3,3'
  }

  const mapping = {
    '1,1': 1,
    '2,1': 2,
    '3,2': 3,
    '4,2': 4,
    '2,2': 5,
    '3,3': 6,
    '4,3': 7
  };
  return mapping[tt] || null;
}
