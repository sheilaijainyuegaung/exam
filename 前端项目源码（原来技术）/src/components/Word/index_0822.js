/* eslint-disable */
import mammoth from 'mammoth'
import html2canvas from 'html2canvas'
//import * as pdfjsLib from 'pdfjs-dist'
// 设置 PDF.js worker 路径
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`

const chineseNoRegs = [/一、/, /二、/, /三、/, /四、/, /五、/, /六、/, /七、/, /八、/, /九、/, /十、/, /十一、/, /十二、/, /十三、/, /十四、/, /十五、/, /十六、/, /十七、/, /十八、/, /十九、/, /二十、/]


const top_margin = 6; // 文字上方留白6mm
const bottom_margin = 2; // 文字下方留白2mm
const targetWidth = 2692; // 目标宽度像素
const targetHeight = 3744; // 目标高度像素
const textSafetyMargin = 1; // 文字周围额外安全距离(mm)


// 标准A4尺寸（毫米）
const PDF_WIDTH_MM = 210;
const PDF_HEIGHT_MM = 297;

/**
 * 从PDF页面中提取标题
 * @param {Object} pageTextContent - PDF页面的文本内容对象
 * @returns {string} 提取到的标题
 */
const extractPdfTitle = (pageTextContent) => {
  // 提取并处理页面文本
  //console.log("textcontent:"+pageTextContent);
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

  //下面第二条规则替换了原来的   /.*[试卷试题测试考试][（(].+[)）]/, 
  const titlePatterns = [
    /.*[试卷试题测试考试]$/,
	/.*(试卷|试题|测试|考试)[（(].+[)）]/,
    /^20\d{2}年?.+[试卷试题测试考试]/,
    /.*[年级学科科目].+[试卷试题测试考试]/,
    /.*[单元月中期末]考.*/,
	/.*(同步|练习).*/,
	/.*(单元|检测).*/,
	/.*(学期|年级).*/,
  ]

  let title = ''
  
  let title_num = 3;
  // 查找符合标题特征的文本
  for (const line of lines) {
	if(title_num < 1) break;
    const text = line.text.trim()
	//console.log("for line.text:"+text);
    // 检查文本长度是否在合理范围内
    if (text.length >= 3 && text.length <= 70) {			
		console.log("text.length >= 5 && text.length <= 50,"+text);
      // 检查是否匹配标题模式
      if (titlePatterns.some(pattern => pattern.test(text))) {
		console.log("extractPdfTitle for: "+text );
        title = text;
        break
      }
    }
	title_num--;
  }
  
  //console.log("extractPdfTitle title:"+title);
  // 如果没有找到符合特征的标题，使用第一行文本（长度合适的）
  if (!title) {
	let aa = 0;
	console.log("没有标题");
    for (const line of lines) {
      const text = line.text.trim()
	  console.log("line.text:"+text);
      if (text.length >= 3 && text.length <= 70) {
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


function filterChildScores(obj) {
  if (obj.childScores && obj.childScores.length === 2) {
    const hasZeroScore = obj.childScores.some(child => child.score === 0);
    const hasPositiveScore = obj.childScores.some(child => child.score > 0);
    
    if (hasZeroScore && hasPositiveScore) {
      obj.childScores = obj.childScores.filter(child => child.score > 0);
    }
  }
  
  // 递归处理所有子节点
  if (obj.childScores) {
    obj.childScores.forEach(child => filterChildScores(child));
  }
  
  return obj;
}


/**
 * 从HTML内容中提取分值信息
 * @param {string} htmlContent - 需要处理的HTML内容
 * @returns {Array} 返回提取的分值信息数组
 */
export function extractScores(htmlContent, title) {

  //console.log("extractScores htmlContent:"+htmlContent);
  //console.log("extractScores title:"+title); 
  // 定义标题匹配模式
  const maxLevel = 3

  // 分值提取正则（全局匹配）
  let scorePattern = /[（(]\s*(?:共)?\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/g;
  let scorePattern2 = /[（(]\s*(?:共)?\s*(?!\d+\s*[）)])(?:\d+(?:\.\d+)?\s*分|)\s*[）)]/g;
  //const singleScorePattern = /[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/;

  const singleScorePattern = /[（(]\s*(?:共\s*)?(?:(\d+(?:\.\d+)?)\s*分\s*|)\s*[）)]/;
  const singleScorePattern2 = /[（(]\s*(?:共\s*)?(?:(\d+(?:\.\d+)?)\s*分\s*|)\s*[）)]/;


  // 移除所有图片标签和空白字符
  let contentWithoutImages = htmlContent.replace(/<img[^>]*>/g, '').replace(/（/g, '(').replace(/）/g, ')').replace(/\s+/g, '').trim();
  console.log("0.contentWithoutImages:"+contentWithoutImages);


  if (title) {
    contentWithoutImages = contentWithoutImages.split(title.replace(/\s+/g, '').replace(/（/g, '(').replace(/）/g, ')').trim())[1]
  }


  // 判断试卷是什么类型
  let templateType = getTemplateType(contentWithoutImages);


  contentWithoutImages = contentWithoutImages.replace(/_<\/p><p>_/g, '_');
  contentWithoutImages = contentWithoutImages.replace(/_{2,}/g, "()");
  contentWithoutImages = contentWithoutImages.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接	



  console.log("templateType:"+templateType);
  console.log("contentWithoutImages::"+contentWithoutImages);

  // 构建文本树
   let textTree = processText(contentWithoutImages);
   let textTree2 = processText2(contentWithoutImages);

	textTree = filterChildScores(textTree);
	textTree2 = filterChildScores(textTree2);


   console.log("start textTree:"+JSON.stringify(textTree)); 	
   console.log("start textTree2:"+JSON.stringify(textTree2)); 	




  // 提取分值信息
  let scoresList = extractScoreInfo(textTree);

  // 提取分值信息
  let scoresList2 = extractScoreInfo2(textTree2);
  let treeDepth = getTreeDepth(scoresList);

  scoresList = filterChildScores(scoresList);
  scoresList2 = filterChildScores(scoresList2);

  console.log("scoresList:"+JSON.stringify(scoresList)); 	
  console.log("scoresList2:"+JSON.stringify(scoresList2)); 


 
  let questionType = getQuestionType(templateType, treeDepth);
  //templateType = 3;
  //questionType = 4;
  console.log("templateType:"+templateType+",treeDepth:"+treeDepth + ",questionType:"+questionType);

  // 递归处理文本，构建树结构


  // MODIFICATION: 新增提取分数的函数，用于从文本中提取父节点自身分数
function extractScore(text) {
  const match = text.match(singleScorePattern);
  return match && match[1] ? parseFloat(match[1]) : null;
}

 // 递归处理文本，构建树结构
  function processText(text, level = 0, prevCounter = 0) {	
    let fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接	
    // 匹配连续的纯下划线 <p> 标签，并替换成单个 ()
    fixedText = fixedText.replace(/(<p>_+<\/p>(?:\s*<p>_+<\/p>)*)/g, "()");

    if (!fixedText || fixedText.length === 0) {
        return null;	
    }

	// MODIFICATION: 尝试从当前文本中提取分数（父节点自身分数）
    const parentScore = extractScore(fixedText);

    // MODIFIED START - 完全重写了 level >= maxLevel 的处理逻辑
    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {
      // 查找所有分值和空括号
      const scoreItems = [];
      let lastIndex = 0;
      let match;
      
      // 新的正则表达式，同时匹配分数和空括号
      const combinedPattern = /(\((?:\d+(?:\.\d+)?\s*分)?\)|\(\))/g;
      
      // 遍历所有匹配项（分数和空括号）
      while ((match = combinedPattern.exec(fixedText)) !== null) {
        // 获取匹配项前面的文本
        const precedingText = fixedText.substring(lastIndex, match.index);
        if (precedingText.trim()) {
          scoreItems.push({
            text: precedingText.trim(),
            score: 0,
            childText: []
          });
        }
        
        // 处理匹配到的分数或空括号
        const scoreMatch = match[0].match(singleScorePattern);
        const score = scoreMatch && scoreMatch[1] ? parseFloat(scoreMatch[1]) : 0;
        
        scoreItems.push({
          text: match[0],
          score: score,
          childText: []
        });
        
        lastIndex = combinedPattern.lastIndex;
      }
      
      // 添加最后一段文本
      const remainingText = fixedText.substring(lastIndex).trim();
      if (remainingText) {
        scoreItems.push({
          text: remainingText,
          score: 0,
          childText: []
        });
      }
      
      // 如果有多个项目，计算总分并返回结构
      if (scoreItems.length > 1) {
        const totalScore = parentScore !== null ? parentScore : 
                          scoreItems.reduce((sum, item) => sum + item.score, 0);
        return {
          //text: `(${totalScore}分)`,
		  text: parentScore !== null ? fixedText : `(${totalScore}分)`,
          score: totalScore,
          // 只保留分数项和空括号作为子项
          childText: scoreItems.filter(item => item.text === '()' || item.text.match(/\(\d+(?:\.\d+)?\s*分\)/))
        };
      } else if (scoreItems.length === 1) {
        return scoreItems[0];
      }
      
      return null;
    }
    // MODIFIED END

    let segments = [];
    let tempText = fixedText;

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
          pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．、]`);
        } else {
          pattern = new RegExp(`\\(${counter}\\)`);
        }
        const match = tempText.match(pattern);
        if (!match) {	
          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
        // 确保正确分割第一个小题
        const splitPos = match.index > 0 ? match.index : match[0].length;
        const first = tempText.substring(0, splitPos);
        const rest = tempText.substring(splitPos);	
        segments.push(first);
        tempText = rest;
        counter++;
      }
    }

    // 处理分割后的文本段
    const result = [];
    const counterSeries = [];

    for (let i = 1; i < segments.length; i++) {	  
      const segment = segments[i].trim();
      if (segment) {
        const node = processText(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
        if (node) {
            // MODIFIED START - 修复计数器逻辑
            counterSeries.push(node.length || 1);
            // MODIFIED END
            result.push(node);
        }
      }
    }

    // 如果没有有效的子节点，尝试下一级模式
    if (result.length === 0) {
      return processText(fixedText, level + 1);
    }

	const totalScore = parentScore !== null ? parentScore : 
                      result.reduce((sum, item) => sum + (item.score || 0), 0);
	return {
      text: fixedText,
      score: totalScore,
      childText: result
    };
    //return result;
  }



  function processText000(text, level = 0, prevCounter = 0) {	
    let fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接	
    // 匹配连续的纯下划线 <p> 标签，并替换成单个 ()
    fixedText = fixedText.replace(/(<p>_+<\/p>(?:\s*<p>_+<\/p>)*)/g, "()");

    if (!fixedText || fixedText.length === 0) {
        return null;	
    }

    // MODIFIED START - 完全重写了 level >= maxLevel 的处理逻辑
    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {
      // 查找所有分值和空括号
      const scoreItems = [];
      let lastIndex = 0;
      let match;
      
      // 新的正则表达式，同时匹配分数和空括号
      const combinedPattern = /(\((?:\d+(?:\.\d+)?\s*分)?\)|\(\))/g;
      
      // 遍历所有匹配项（分数和空括号）
      while ((match = combinedPattern.exec(fixedText)) !== null) {
        // 获取匹配项前面的文本
        const precedingText = fixedText.substring(lastIndex, match.index);
        if (precedingText.trim()) {
          scoreItems.push({
            text: precedingText.trim(),
            score: 0,
            childText: []
          });
        }
        
        // 处理匹配到的分数或空括号
        const scoreMatch = match[0].match(singleScorePattern);
        const score = scoreMatch && scoreMatch[1] ? parseFloat(scoreMatch[1]) : 0;
        
        scoreItems.push({
          text: match[0],
          score: score,
          childText: []
        });
        
        lastIndex = combinedPattern.lastIndex;
      }
      
      // 添加最后一段文本
      const remainingText = fixedText.substring(lastIndex).trim();
      if (remainingText) {
        scoreItems.push({
          text: remainingText,
          score: 0,
          childText: []
        });
      }
      
      // 如果有多个项目，计算总分并返回结构
      if (scoreItems.length > 1) {
        const totalScore = scoreItems.reduce((sum, item) => sum + item.score, 0);
        return {
          text: `(${totalScore}分)`,
          score: totalScore,
          // 只保留分数项和空括号作为子项
          childText: scoreItems.filter(item => item.text === '()' || item.text.match(/\(\d+(?:\.\d+)?\s*分\)/))
        };
      } else if (scoreItems.length === 1) {
        return scoreItems[0];
      }
      
      return null;
    }
    // MODIFIED END

    let segments = [];
    let tempText = fixedText;

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
          pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．、]`);
        } else {
          pattern = new RegExp(`\\(${counter}\\)`);
        }
        const match = tempText.match(pattern);
        if (!match) {	
          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
        // 确保正确分割第一个小题
        const splitPos = match.index > 0 ? match.index : match[0].length;
        const first = tempText.substring(0, splitPos);
        const rest = tempText.substring(splitPos);	
        segments.push(first);
        tempText = rest;
        counter++;
      }
    }

    // 处理分割后的文本段
    const result = [];
    const counterSeries = [];

    for (let i = 1; i < segments.length; i++) {	  
      const segment = segments[i].trim();
      if (segment) {
        const node = processText(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
        if (node) {
            // MODIFIED START - 修复计数器逻辑
            counterSeries.push(node.length || 1);
            // MODIFIED END
            result.push(node);
        }
      }
    }

    // 如果没有有效的子节点，尝试下一级模式
    if (result.length === 0) {
      return processText(fixedText, level + 1);
    }

    return result;
  }



  function processText111(text, level = 0, prevCounter = 0) {	
	//console.log("-------processText text:"+text);
    let fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接	
	//fixedText = fixedText.replace(/_{2,}/g, "()");
	// 匹配连续的纯下划线 <p> 标签，并替换成单个 ()
	fixedText = fixedText.replace(/(<p>_+<\/p>(?:\s*<p>_+<\/p>)*)/g, "()");


    if (!fixedText || fixedText.length === 0) {
		//console.log("!fixedText or fixedText.length === 0");
		return null;	
	}else{
		//console.log("fixedText and fixedText.length > 0");
	}

    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {
      // 查找所有分值
      const scores = Array.from(fixedText.matchAll(scorePattern)).map(match => parseFloat(match[1]));	    
	  //console.log("查找所有分值processText scores:"+JSON.stringify(scores)); 
      // 如果有多个分值，创建子节点
      if (scores.length > 1) {
		// 跳过第一个总分值（8分），从第二个分值开始
        const childScores = scores.slice(0);
		let score_tmp = scores.reduce((a, b) => a + b, 0); 
		
		return {
          text: isNaN(score_tmp)?`(0分)`:`(${score_tmp}分)`,
          score: isNaN(score_tmp)?0:score_tmp,
          childText: childScores.map(score => ({
            text: isNaN(score)?`(0分)`:`(${score}分)`,
            score: isNaN(score)?0:score,
            childText: []
          }))
        };


      } else {
        // 单个分值的情况
        const scoreMatch = fixedText.match(singleScorePattern);
		//console.log("单个分值的情况fixedText:"+fixedText);
		//console.log("单个分值的情况scoreMatch:"+JSON.stringify(scoreMatch)); 
		if(scoreMatch===null){
			 return null;

		}else{			
			
			if(scoreMatch[0]=='()'){
				return {
				  text: '()',
				  score: 0,
				  childText: []
				}
			}else{
				const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;
				// 如果分值为0，返回null
				return score > 0 ? {
				  text: fixedText,
				  score: score,
				  childText: []
				} : null;
			}

		}




      }
    }

    let segments = [];
    let tempText = fixedText;

	
    // 根据不同的模式类型使用不同的匹配逻辑
    if (level === 0) { // 中文数字标题

		//console.log("***start tempText level 0:"+tempText); 

      // 按照 chineseNoRegs 数组顺序尝试匹配
      for (let i = 0; i < chineseNoRegs.length; i++) {
        const pattern = chineseNoRegs[i];
        const match = tempText.match(pattern);
        if (!match) {
			//console.log("0.for tempText未匹配到数组序号，返回:"+tempText); 
            segments.push(tempText);
            break; // 如果匹配中断，停止当前级别的匹配
        }		
		//console.log("0.for match[0]:"+match[0]); 
        const [first, rest] = splitOnce(tempText, match[0]);
		//console.log("0.for first:"+first); 
		//console.log("0.first i:"+i); 
		//console.log("0.for rest:"+rest); 
        segments.push(first);
        tempText = rest;
      }	  
	  //console.log("0.end for segments:"+JSON.stringify(segments)); 
	  //console.log("0.tempText:"+tempText); 

    } else { // 阿拉伯数字标题或括号数字标题

		//console.log("***start tempText level <>0:"+tempText); 

		  let counter = templateType !== '4' ? 1 : prevCounter + 1;
		  while (true) {
			let pattern;

			//console.log(">0.while counter:"+counter); 
			if (level === 1) {
			  // 当type是pdf时从头部开始匹配		  
			  pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．、]`);
			  //pattern = new RegExp(`(?:<p>)?${counter}[.．、]\\(?\\d+分\\)?`);
			  //console.log(">0.while level 1 pattern "+`(?<!<td\\s*>)<p>${counter}[.．、]`);
			} else {
			  pattern = new RegExp(`\\(${counter}?\\)`);
			  //console.log(">0.while <>level 1 pattern "+`\\(${counter}?\\)`);
			}
			const match = tempText.match(pattern);
			if (!match) {	
			  //console.log(">0.while 没有匹配到序数:"); 
			  segments.push(tempText);
			  break; // 如果匹配中断，停止当前级别的匹配
			}
			//const [first, rest] = splitOnce(tempText, match[0]);
			// 确保正确分割第一个小题
			const splitPos = match.index > 0 ? match.index : match[0].length;
			const first = tempText.substring(0, splitPos);
			const rest = tempText.substring(splitPos);			
			//console.log(">0.while first:"+first); 
			//console.log(">0.while rest:"+rest); 
			segments.push(first);
			//console.log("0.while segments push first:"+JSON.stringify(first)); 
			//console.log("0.while segments first:"+JSON.stringify(segments)); 
			tempText = rest;
			counter++;
		  }//end while

	}

    // 处理分割后的文本段
    const result = [];
    const counterSeries = [];

	//console.log("2.before for segments:"+JSON.stringify(segments)); 

    for (let i = 1; i < segments.length; i++) {	  
      const segment = segments[i].trim();
	  //console.log("2.for segment:"+JSON.stringify(segment) + ",loop:"+i); 

	  //console.log("processText("+ (level + 1)  + ","+  counterSeries.reduce((a, b) => a + b, 0)); 

      if (segment) {
		const node = processText(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
        if (node) {
			//console.log(" if 2.node:"+JSON.stringify(node)); 
            counterSeries.push(node.length)
            result.push(node);
        }else{
			//console.log(" if 2.not node:"+JSON.stringify(node)); 
		}

      }else{		  
		  //console.log(" if 2.not segment:"+JSON.stringify(segment)); 
		}
    }

    // 如果没有有效的子节点，尝试下一级模式
    if (result.length === 0) {
      return processText(fixedText, level + 1);
    }

    return result;
  }
	


// 递归处理文本，构建树结构
  function processText2(text, level = 0, prevCounter = 0) {	
	//console.log("-------processText2 text:"+text);
    let fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接	
	// 匹配连续的纯下划线 <p> 标签，并替换成单个 ()
	fixedText = fixedText.replace(/(<p>_+<\/p>(?:\s*<p>_+<\/p>)*)/g, "()");

    if (!fixedText || fixedText.length === 0) {
		//console.log("!fixedText or fixedText.length === 0");
		return null;	
	}else{
		//console.log("fixedText and fixedText.length > 0");
	}

	//console.log("fixedText:"+fixedText);
    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {	


		let scoreMatches = Array.from(fixedText.matchAll(scorePattern2));
		console.log("processText2 scoreMatches:"+JSON.stringify(scoreMatches)); 

		if(scoreMatches.length > 1){		
				
				// 定义正则：匹配 (数字分) 或 ( 数字 分 ) 等变体
				const scorePattern = /[（(]\s*共?\s*\d+\s*分\s*[）)]/;
				// 过滤掉包含 "数字+分" 的项
				scoreMatches = scoreMatches.filter(
				  match => !scorePattern.test(match[0])
				);

		}
		//console.log("processText2 scoreMatches2:"+JSON.stringify(scoreMatches)); 
		const scores = scoreMatches.map(match => parseFloat(match[1]));
		console.log("processText2 scoreMatches2:"+JSON.stringify(scoreMatches)); 
	  
	  
	  console.log("processText2 scores:"+JSON.stringify(scores)); 

      // 如果有多个分值，创建子节点
      if (scores.length > 1) {
		// 跳过第一个总分值（8分），从第二个分值开始
        const childScores = scores.slice(0);

		let score_tmp = scores.reduce((a, b) => a + b, 0); 	
		

		/*
	
        return {
          text: isNaN(score_tmp)?`(0分)`:`(${score}分)`,
          score: isNaN(score_tmp)?0:score_tmp,
          childText: childScores.map(score => ({
            text: isNaN(score)?`(0分)`:`(${score}分)`,
            score: isNaN(score)?0:score,
            childText: []
          }))
        };
		*/



		 // 【修改1：父节点分数从自身文本提取，而非子节点总和】
        // 提取当前节点自身的分数（优先匹配带“共”或直接标注的分数）
        const selfScoreMatch = fixedText.match(/[（(]\s*(?:共)?\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/);
        const selfScore = selfScoreMatch ? parseFloat(selfScoreMatch[1]) : 0;

        return {
          text: fixedText,  // 保留原始文本
          score: selfScore,  // 使用自身提取的分数
          childText: childScores.map(score => ({
            text: isNaN(score)?`(0分)`:`(${score}分)`,
            score: isNaN(score)?0:score,
            childText: []
          }))
        };

		

      } else {

        // 单个分值的情况
        const scoreMatch = fixedText.match(singleScorePattern2);
		//console.log("单个分值的情况fixedText:"+fixedText);
		//console.log("单个分值的情况scoreMatch:"+JSON.stringify(scoreMatch)); 
		if(scoreMatch===null){
			 return null;
		}else{						
			if(scoreMatch[0]=='()'){
				return {
				  text: '()',
				  score: 0,
				  childText: []
				}
			}else{
				const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;
				// 如果分值为0，返回null
				return score > 0 ? {
				  text: fixedText,
				  score: score,
				  childText: []
				} : null;
			}

		}



      }
    }

    let segments = [];
    let tempText = fixedText;

	//console.log("***tempText:"+tempText); 

    // 根据不同的模式类型使用不同的匹配逻辑
    if (level === 0) { // 中文数字标题
		
		console.log("先判断level是否0然后开始"); 

      // 按照 chineseNoRegs 数组顺序尝试匹配
      for (let i = 0; i < chineseNoRegs.length; i++) {
        const pattern = chineseNoRegs[i];
        const match = tempText.match(pattern);
        if (!match) {
          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
		
		//console.log("0.match[0]:"+match[0]); 
        const [first, rest] = splitOnce(tempText, match[0]);
		//console.log("0.first:"+first); 
		//console.log("0.first i:"+i); 
		//console.log("0.rest:"+rest); 

        segments.push(first);
        tempText = rest;
      }
	  
	  //console.log("0.segments:"+JSON.stringify(segments)); 
	  //console.log("0.tempText:"+tempText); 


    } else { // 阿拉伯数字标题或括号数字标题
		//console.log(">0.tempText:"+tempText); 


      let counter = templateType !== '4' ? 1 : prevCounter + 1;

      while (true) {
        let pattern;

		//console.log(">0.while counter:"+counter); 
        if (level === 1) {
          // 当type是pdf时从头部开始匹配		  
          pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．、]`);

        } else {
          pattern = new RegExp(`\\(${counter}?\\)`);

        }
        const match = tempText.match(pattern);
        if (!match) {	
			//console.log("没有匹配到!match:"); 

          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
        const [first, rest] = splitOnce(tempText, match[0]);
		
		//console.log(">0.while first:"+first); 
		//console.log(">0.while rest:"+rest); 
        segments.push(first);
		//console.log("0.while segments push first:"+JSON.stringify(first)); 
		//console.log("0.while segments first:"+JSON.stringify(segments)); 

        tempText = rest;
        counter++;
      }//end while


  }
    // 处理分割后的文本段
    const result = [];
    const counterSeries = []
	
	//console.log(" 1.segments.length:"+ segments.length);
	//console.log(" 1.segments:"+JSON.stringify(segments)); 

    for (let i = 1; i < segments.length; i++) {
      const segment = segments[i].trim();
	  //console.log("i:"+i);
	  //console.log("segment length:"+segment);
      if (segment) {
		  //console.log(" 2.segment:"+JSON.stringify(segment)); 
		  //console.log(" 2.level:"+(level + 1)); 
		  const node = processText2(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
		  //console.log(" 2.node:"+JSON.stringify(node)); 

        if (node) {
			//console.log(" if 2.node:"+JSON.stringify(node)); 
          counterSeries.push(node.length)
          result.push(node);
        }
      }
    }

    // 如果没有有效的子节点，尝试下一级模式
    if (result.length === 0) {
      return processText2(fixedText, level + 1);
    }

    return result;
  }

	// 递归处理文本，构建树结构
  function processText211(text, level = 0, prevCounter = 0) {	
	//console.log("-------processText2 text:"+text);
    let fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接	
	// 匹配连续的纯下划线 <p> 标签，并替换成单个 ()
	fixedText = fixedText.replace(/(<p>_+<\/p>(?:\s*<p>_+<\/p>)*)/g, "()");

    if (!fixedText || fixedText.length === 0) {
		//console.log("!fixedText or fixedText.length === 0");
		return null;	
	}else{
		//console.log("fixedText and fixedText.length > 0");
	}

	//console.log("fixedText:"+fixedText);
    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {	


		let scoreMatches = Array.from(fixedText.matchAll(scorePattern2));
		console.log("processText2 scoreMatches:"+JSON.stringify(scoreMatches)); 

		if(scoreMatches.length > 1){		
				
				// 定义正则：匹配 (数字分) 或 ( 数字 分 ) 等变体
				const scorePattern = /[（(]\s*共?\s*\d+\s*分\s*[）)]/;
				// 过滤掉包含 "数字+分" 的项
				scoreMatches = scoreMatches.filter(
				  match => !scorePattern.test(match[0])
				);

		}
		//console.log("processText2 scoreMatches2:"+JSON.stringify(scoreMatches)); 
		const scores = scoreMatches.map(match => parseFloat(match[1]));
		console.log("processText2 scoreMatches2:"+JSON.stringify(scoreMatches)); 
	  
	  
	  console.log("processText2 scores:"+JSON.stringify(scores)); 

      // 如果有多个分值，创建子节点
      if (scores.length > 1) {
		// 跳过第一个总分值（8分），从第二个分值开始
        const childScores = scores.slice(0);

		let score_tmp = scores.reduce((a, b) => a + b, 0); 		
	
        return {
          text: isNaN(score_tmp)?`(0分)`:`(${score}分)`,
          score: isNaN(score_tmp)?0:score_tmp,
          childText: childScores.map(score => ({
            text: isNaN(score)?`(0分)`:`(${score}分)`,
            score: isNaN(score)?0:score,
            childText: []
          }))
        };
		

      } else {

        // 单个分值的情况
        const scoreMatch = fixedText.match(singleScorePattern2);
		//console.log("单个分值的情况fixedText:"+fixedText);
		//console.log("单个分值的情况scoreMatch:"+JSON.stringify(scoreMatch)); 
		if(scoreMatch===null){
			 return null;
		}else{						
			if(scoreMatch[0]=='()'){
				return {
				  text: '()',
				  score: 0,
				  childText: []
				}
			}else{
				const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;
				// 如果分值为0，返回null
				return score > 0 ? {
				  text: fixedText,
				  score: score,
				  childText: []
				} : null;
			}

		}



      }
    }

    let segments = [];
    let tempText = fixedText;

	//console.log("***tempText:"+tempText); 

    // 根据不同的模式类型使用不同的匹配逻辑
    if (level === 0) { // 中文数字标题
		
		console.log("先判断level是否0然后开始"); 

      // 按照 chineseNoRegs 数组顺序尝试匹配
      for (let i = 0; i < chineseNoRegs.length; i++) {
        const pattern = chineseNoRegs[i];
        const match = tempText.match(pattern);
        if (!match) {
          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
		
		//console.log("0.match[0]:"+match[0]); 
        const [first, rest] = splitOnce(tempText, match[0]);
		//console.log("0.first:"+first); 
		//console.log("0.first i:"+i); 
		//console.log("0.rest:"+rest); 

        segments.push(first);
        tempText = rest;
      }
	  
	  //console.log("0.segments:"+JSON.stringify(segments)); 
	  //console.log("0.tempText:"+tempText); 


    } else { // 阿拉伯数字标题或括号数字标题
		//console.log(">0.tempText:"+tempText); 


      let counter = templateType !== '4' ? 1 : prevCounter + 1;

      while (true) {
        let pattern;

		//console.log(">0.while counter:"+counter); 
        if (level === 1) {
          // 当type是pdf时从头部开始匹配		  
          pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．、]`);

        } else {
          pattern = new RegExp(`\\(${counter}?\\)`);

        }
        const match = tempText.match(pattern);
        if (!match) {	
			//console.log("没有匹配到!match:"); 

          segments.push(tempText);
          break; // 如果匹配中断，停止当前级别的匹配
        }
        const [first, rest] = splitOnce(tempText, match[0]);
		
		//console.log(">0.while first:"+first); 
		//console.log(">0.while rest:"+rest); 
        segments.push(first);
		//console.log("0.while segments push first:"+JSON.stringify(first)); 
		//console.log("0.while segments first:"+JSON.stringify(segments)); 

        tempText = rest;
        counter++;
      }//end while


  }
    // 处理分割后的文本段
    const result = [];
    const counterSeries = []
	
	//console.log(" 1.segments.length:"+ segments.length);
	//console.log(" 1.segments:"+JSON.stringify(segments)); 

    for (let i = 1; i < segments.length; i++) {
      const segment = segments[i].trim();
	  //console.log("i:"+i);
	  //console.log("segment length:"+segment);
      if (segment) {
		  //console.log(" 2.segment:"+JSON.stringify(segment)); 
		  //console.log(" 2.level:"+(level + 1)); 
		  const node = processText2(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
		  //console.log(" 2.node:"+JSON.stringify(node)); 

        if (node) {
			//console.log(" if 2.node:"+JSON.stringify(node)); 
          counterSeries.push(node.length)
          result.push(node);
        }
      }
    }

    // 如果没有有效的子节点，尝试下一级模式
    if (result.length === 0) {
      return processText2(fixedText, level + 1);
    }

    return result;
  }



 // 提取分值信息 - 修改后的版本
  function extractScoreInfo(node, parent = null, grandParent = null, siblings = [], parentSiblings = []) {
    if (!node) return null;

    // 如果是数组（多个同级节点）
    if (Array.isArray(node)) {
      const validNodes = node.map((item, index) =>
        extractScoreInfo(
          item,
          null,
          null,
          node.slice(0, index),
          []
        )
      ).filter(Boolean);

      if (validNodes.length === 0) return '';

      // 计算总分并构建新的结构
      const totalScore = validNodes.reduce((sum, item) => sum + item.score, 0);
      return {
        score: (totalScore == null || isNaN(totalScore)) ? 0 : totalScore,
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

    // 如果当前节点分值为0且没有有效的子节点分值，返回空结构
    if (node.score === 0 && childScores.length === 0) {
      return {
        score: 0,
        childScores: []
      };
    }

    let currentScore = node.score;
    let finalChildScores = childScores;

    // 新增的逻辑：处理 childScores，只考虑长度大于2的数组
    if (finalChildScores.length > 1) {
      const firstScore = finalChildScores[0].score;
      const remainingSum = finalChildScores.slice(1).reduce((sum, item) => sum + item.score, 0);

      if (firstScore !== 0 && finalChildScores.length > 2 && firstScore === remainingSum) {
        // 情况1：第一项等于后面所有项之和
        return {
          score: (firstScore == null || isNaN(firstScore)) ? 0 : firstScore,
          childScores: finalChildScores.slice(1)
        };
      } else {
        // 情况2：第一项不等于后面所有项之和
        let score_tmp = finalChildScores.reduce((sum, item) => sum + item.score, 0);
       
		
		// 只有当父节点没有分数时才使用子节点之和
        if (node.score === 0 || node.score === null || isNaN(node.score)) {
          return {
            score: (score_tmp == null || isNaN(score_tmp)) ? 0 : score_tmp,
            childScores: finalChildScores
          };
        } else {
          // 父节点有分数，保留父节点分数
          return {
            score: node.score,
            childScores: finalChildScores
          };
        }
		 
      }
    }

    // 修改的关键部分：只有当当前节点没有分数时才使用子节点分数之和
    if (finalChildScores.length > 0 && (node.score === 0 || node.score === null || isNaN(node.score))) {
      currentScore = finalChildScores.reduce((sum, item) => sum + item.score, 0);
    }else {
        // 父节点有分数，保留父节点分数
        currentScore = node.score;
    }

    return {
      score: (currentScore == null || isNaN(currentScore)) ? 0 : currentScore,
      childScores: finalChildScores.length > 0 ? finalChildScores : []
    };
  }

   // 提取分值信息
  function extractScoreInfo111(node, parent = null, grandParent = null, siblings = [], parentSiblings = []) {
	//console.log("***extractScoreInfo node:"+JSON.stringify(node)); 
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
	  //).filter(item => item !== ''); // 修改：只过滤掉空字符串，保留其他 falsy 值

      if (validNodes.length === 0) return '';

      // 计算总分并构建新的结构
      const totalScore = validNodes.reduce((sum, item) => sum + item.score, 0);
      return {
        score: (totalScore==null || totalScore==NaN)?0:totalScore,
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
      //return '';
	  return {
          score: 0,
          childScores: []
        };
    }

    let currentScore = node.score;
    let finalChildScores = childScores;

    // 新增的逻辑：处理 childScores，只考虑长度大于2的数组
    if (finalChildScores.length > 1) {
      const firstScore = finalChildScores[0].score;
      const remainingSum = finalChildScores.slice(1).reduce((sum, item) => sum + item.score, 0);

	  //console.log("firstScore:"+firstScore+",finalChildScores:"+JSON.stringify(finalChildScores));
	  //console.log("remainingSum:"+remainingSum);

      if (firstScore !== 0 && finalChildScores.length > 2 && firstScore === remainingSum) {
        // 情况1：第一项等于后面所有项之和
        return {
          score: (firstScore==null || firstScore==NaN)?0:firstScore,
          childScores: finalChildScores.slice(1)
        };
      } else {
        // 情况2：第一项不等于后面所有项之和
		//console.log("情况2：第一项不等于后面所有项之和score:"+finalChildScores.reduce((sum, item) => sum + item.score, 0));

		let score_tmp = finalChildScores.reduce((sum, item) => sum + item.score, 0);

        return {
          score: (score_tmp==null || score_tmp==NaN)?0:score_tmp,
          childScores: finalChildScores
        };
      }
    }

    // 如果有子节点，使用子节点分数之和
    if (finalChildScores.length > 0) {
      currentScore = finalChildScores.reduce((sum, item) => sum + item.score, 0);
    }

    return {
      score: currentScore==null?0:currentScore,
      childScores: finalChildScores.length > 0 ? finalChildScores : ''
    };
  }

  // 提取分值信息
  function extractScoreInfo2(node, parent = null, grandParent = null, siblings = [], parentSiblings = []) {
    if (!node) return null;
	
	 if (Array.isArray(node)) {
		//console.log("extractScoreInfo2 node array:"+JSON.stringify(node));
	 }else{
		//console.log("extractScoreInfo2 node:"+JSON.stringify(node));
	 }

    // 如果是数组（多个同级节点）
    if (Array.isArray(node)) {

	  //console.log("isArray node extractScoreInfo2:"+JSON.stringify(node));

      const validNodes = node.map((item, index) =>
        extractScoreInfo2(
          item,
          null,
          null,
          node.slice(0, index), // 传递当前节点之前的兄弟节点
          []
        )
     // ).filter(Boolean);
	   ).filter(item => item !== ''); // 修改：只过滤掉空字符串，保留其他 falsy 值



		 // console.log("validNodes:"+JSON.stringify(validNodes));
		if (validNodes.length === 0){
			//console.log("validNodes.length == 0");
		}else{
			//console.log("validNodes.length <> 0");
		}


      if (validNodes.length === 0) return '';

      // 计算总分并构建新的结构
      const totalScore = validNodes.reduce((sum, item) => sum + item.score, 0);

	 // console.log("totalScore:"+totalScore)
      return {
        score: (totalScore==null || isNaN(totalScore))?0:totalScore,
        childScores: validNodes
      };


    }


    // 处理子节点的分值
    const childScores = node.childText.length > 0
      ? node.childText.map((child, index) =>
        extractScoreInfo2(
          child,
          node,
          parent,
          node.childText.slice(0, index),
          siblings
        )
     // ).filter(Boolean)
        ).filter(item => item !== '') // 修改：同上
	  : [];

    // 如果当前节点分值为0且没有有效的子节点分值，返回null
    if (node.score === 0 && childScores.length === 0) {
		//console.log("处理子节点的分值 node:"+JSON.stringify(node));
        //return '';

		return {
          score: 0,
          childScores: []
        };

    }

    let currentScore = node.score;
    let finalChildScores = childScores;

    // 新增的逻辑：处理 childScores，只考虑长度大于2的数组
    if (finalChildScores.length > 1) {

      const firstScore = finalChildScores[0].score;
      const remainingSum = finalChildScores.slice(1).reduce((sum, item) => sum + item.score, 0);

	 // console.log("firstScore:"+firstScore+",finalChildScores:"+JSON.stringify(finalChildScores));
	  //console.log("remainingSum:"+remainingSum);

      if (firstScore !== 0 &&  finalChildScores.length > 2 && firstScore === remainingSum) {
        // 情况1：第一项等于后面所有项之和
        return {
          score: (firstScore==null || isNaN(firstScore))?0:firstScore,
          childScores: finalChildScores.slice(1)
        };
      } else {
        // 情况2：第一项不等于后面所有项之和

		//console.log("情况2：第一项不等于后面所有项之和score:"+finalChildScores.reduce((sum, item) => sum + item.score, 0));
		let score_tmp = finalChildScores.reduce((sum, item) => sum + item.score, 0);

		  // 只有当父节点没有分数时才使用子节点之和
        if (node.score === 0 || node.score === null || isNaN(node.score)) {
          return {
            score: (score_tmp == null || isNaN(score_tmp)) ? 0 : score_tmp,
            childScores: finalChildScores
          };
        } else {
          // 父节点有分数，保留父节点分数
          return {
            score: node.score,
            childScores: finalChildScores
		 };
		}



      }
    }

    // 如果有子节点，使用子节点分数之和
	// 修改的关键部分：只有当当前节点没有分数时才使用子节点分数之和
    if (finalChildScores.length > 0 && (node.score === 0 || node.score === null || isNaN(node.score))) {
      currentScore = finalChildScores.reduce((sum, item) => sum + item.score, 0);
    }else {
        // 父节点有分数，保留父节点分数
        currentScore = node.score;
    }

    return {
      //score: currentScore==null?0:currentScore,
	  score: (currentScore == null || isNaN(currentScore)) ? 0 : currentScore,
      childScores: finalChildScores.length > 0 ? finalChildScores : []
    };




  }//extractScoreInfo2


  // 判断试卷是什么类型
/*
Template判断
情况1：只有中文数字标题
情况2：只有阿拉伯数字标题
情况3：同时存在中文和阿拉伯数字标题，且阿拉伯数字不连续
情况4：同时存在中文和阿拉伯数字标题，且阿拉伯数字连续
*/

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

    // 在整个文本中检查阿拉伯数字标题
    let foundNumbers = new Set(); // 使用Set来收集所有找到的数字
    let maxNumber = 0;
    
    // 查找所有可能的阿拉伯数字编号
    for (let counter = 1; counter <= 100; counter++) { // 设置合理的上限防止无限循环
        const pattern = new RegExp(`(?<!<td\\s*>)(<p>${counter}[.．、]|\\(${counter}\\))`);
        const match = text.match(pattern);
        if (match) {
            foundNumbers.add(counter);
            if (counter === 1) hasArabicNo = true;
            if (counter > maxNumber) maxNumber = counter;
        }
    }

    // 将找到的数字按顺序存入arabicNumbers
    arabicNumbers = Array.from(foundNumbers).sort((a, b) => a - b);

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
        const isSequential = arabicNumbers.length > 0 && 
                           arabicNumbers[arabicNumbers.length - 1] === arabicNumbers.length &&
                           arabicNumbers.every((num, index) => num === index + 1);

        // 情况3和4：根据阿拉伯数字是否连续返回不同类型
        return isSequential ? '4' : '3';
    }

    return null;
}


  function getTemplateType2(text) {

	console.log("getTemplateType text:" + text);
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
        //let pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．]`);
		let pattern = new RegExp(`(?<!<td\\s*>)(<p>${counter}[.．、]|\\(${counter}\\))`);
        let match = segment.match(pattern);
        if (!match) {
          counter = 1;
          //pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．]`);
		  pattern = new RegExp(`(?<!<td\\s*>)(<p>${counter}[.．、]|\\(${counter}\\))`);
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
	scoresList2,
  };

}




export const processHtmlContent = async (htmlContent) => {
  try {
    const mainPagesList = []
    const answerPagesList = []


	console.log("processHtmlContent htmlContent:"+htmlContent);

    // 获取试卷标题，第一个strong标签包裹的内容
    //const title = htmlContent.match(/<strong>(.*?)<\/strong>/)[1]

	const title = htmlContent.match(/<p>(.*?)<\/p>/)[1]


	console.log("processHtmlContent title:"+title);

    // 将em标签中间的空格替换为_
    const processedContent = htmlContent
      .replace(/<em>([^<]*)<\/em>/g, (match, p1) => `${p1.replace(/\s+/g, (space) => '_'.repeat(space.length))}`)
      .replace(/（/g, '(').replace(/）/g, ')')

    let splitContent = processedContent.split(
      /<p><strong>答案<\/strong><\/p>/
    )
	//console.log("splitContent[0]:"+splitContent[0]);
	//console.log("splitContent[1]:"+splitContent[1]);
	if(splitContent[1]){
			const mainContent = splitContent[0];
			const answerContent =  `<p><strong>答案</strong></p>${splitContent[1]}` ;
	}else{
		let splitContent2 = processedContent.split(/<p>(答案页)<\/p>/);
		if(splitContent2[1]){
			const mainContent = splitContent2[0];
			const answerContent = `<p><strong>答案</strong></p>${splitContent2[1]}` ;
		}else{

			let splitContent3 = processedContent.split(/<p>答案解析部分<\/p>/);

			if(splitContent3[1]){
				const mainContent = splitContent3[0];
				const answerContent = `<p><strong>答案解析部分</strong></p>${splitContent3[1]}` ;
			}else{
				const mainContent = splitContent[0];
				const answerContent =  '';
			}
		}

	}
    
    const { scoresList, questionType, scoresList2 } = extractScores(mainContent.replace(title, ''))


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
	  scores2: scoresList2,
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

		//console.log("handleWordDocument:"+result.value);

    return await processHtmlContent(result.value)
  } catch (error) {
    throw new Error('Word文档处理失败：' + error.message)
  }
}



function mergeScores(primary, secondary) {
    // 如果 primary 或 secondary 不存在，直接返回另一个
    if (!primary) return secondary;
    if (!secondary) return primary;

    // 合并逻辑：选择子分类更多的结构作为主结构
    const merged = {
        score: primary.score || 0,  // 默认用 primary 的分数
        childScores: mergeChildScores(primary.childScores, secondary.childScores)
    };

    return merged;

    // 递归合并子分类
    function mergeChildScores(primaryChildren, secondaryChildren) {
        // 如果其中一个不存在，直接返回另一个
        if (!primaryChildren) return secondaryChildren;
        if (!secondaryChildren) return primaryChildren;

        // 判断哪个子分类更多
        const primaryChildCount = getChildCount(primaryChildren);
        const secondaryChildCount = getChildCount(secondaryChildren);

        // 选择子分类更多的作为主结构
        const mainChildren = primaryChildCount >= secondaryChildCount ? primaryChildren : secondaryChildren;
        const otherChildren = primaryChildCount >= secondaryChildCount ? secondaryChildren : primaryChildren;

        // 如果是数组，按索引合并
        if (Array.isArray(mainChildren)) {
            return mainChildren.map((child, index) => {
                const otherChild = Array.isArray(otherChildren) ? otherChildren[index] : [];

                return {
                    score: child.score || (otherChild ? otherChild.score : 0),
                    childScores: mergeChildScores(child.childScores, otherChild ? otherChild.childScores : [])
                };
            });
        }
        // 如果是对象，递归合并
        else if (typeof mainChildren === 'object') {
            const mergedChild = {
                score: mainChildren.score || (otherChildren ? otherChildren.score : 0),
                childScores: mergeChildScores(mainChildren.childScores, otherChildren ? otherChildren.childScores : [])
            };
            return mergedChild;
        }

        // 默认返回 mainChildren（理论上不会走到这里）
        return mainChildren;
    }

    // 计算子分类数量（支持数组和对象）
    function getChildCount(children) {
        if (!children) return 0;
        if (Array.isArray(children)) return children.length;
        if (typeof children === 'object') return 1;  // 单对象算 1 个子分类
        return 0;
    }
}




function mergeScores2(primary, secondary) {
    // Create a new object with primary's top score but secondary's structure
	//console.log("primary.score:"+primary.score);
    const merged = {
        score: primary.score,
        childScores: mergeChildScores(primary.childScores, secondary.childScores)
    };
    
    return merged;
    
    // Helper function to recursively merge child scores
    function mergeChildScores(primaryChildren, secondaryChildren) {
        // If secondary has no children or primary has no children, return secondary's structure
        if (!secondaryChildren || !primaryChildren) {
            return secondaryChildren || primaryChildren;
        }
        
        // If secondary children is an array but primary isn't, use secondary's structure with 0 scores
        if (Array.isArray(secondaryChildren) && !Array.isArray(primaryChildren)) {
            return secondaryChildren.map(child => ({
                score: 0,
                childScores: mergeChildScores(null, child.childScores)
            }));
        }
        
        // If both are arrays, merge them
        if (Array.isArray(secondaryChildren) && Array.isArray(primaryChildren)) {
            return secondaryChildren.map((child, index) => {
                // Use the corresponding primary child if it exists at this index
                const primaryChild = primaryChildren[index];
                
                return {
                    score: primaryChild ? primaryChild.score : 0,
                    childScores: mergeChildScores(
                        primaryChild ? primaryChild.childScores : null,
                        child.childScores
                    )
                };
            });
        }
        
        // Fallback - return secondary's structure with 0 scores
        return secondaryChildren;
    }
}

// 核心改进：精确检测内容边界框
function detectContentBoundingBox(ctx, canvas) {
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const data = imageData.data;
  
  let minX = canvas.width;
  let minY = canvas.height;
  let maxX = 0;
  let maxY = 0;

  // 扫描所有像素点
  for (let y = 0; y < canvas.height; y++) {
    for (let x = 0; x < canvas.width; x++) {
      const idx = (y * canvas.width + x) * 4;
      // 非白色像素检测（RGB值不全为255）
      if (data[idx] < 250 || data[idx+1] < 250 || data[idx+2] < 250) {
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
  }

  // 返回内容边界框（增加5px安全边距）
  return {
    left: Math.max(0, minX - 5),
    top: Math.max(0, minY - 5),
    right: Math.min(canvas.width, maxX + 5),
    bottom: Math.min(canvas.height, maxY + 5)
  };
}






export const handlePdfDocument = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    const totalPages = pdf.numPages;

    let answerStartPage = null;
    let htmlContent = '';
    const mainPages = [];
    const answerPages = [];
    let allLines = [];

    // 获取第一页标题
    const firstPage = await pdf.getPage(1);
    const firstPageText = await firstPage.getTextContent();
    const title = extractPdfTitle(firstPageText);

    for (let i = 1; i <= totalPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items.map(item => item.str).join(' ');
      
      // 检测答案页起始位置
      const answerPattern = /(^|\s|[。．.、\n(（])(参考)?答案(页|解析部分)?($|\s|[：:．.、\n)）])/g;
      if (answerPattern.test(pageText) && !answerStartPage) {
        answerStartPage = i;
      }

      // 高分辨率渲染配置
      const renderScale = 5.0; // 更高缩放确保细节清晰
      const viewport = page.getViewport({ scale: renderScale });
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      // 渲染PDF页面
      await page.render({
        canvasContext: context,
        viewport: viewport
      }).promise;

      // ********** 关键1：单位转换与边距计算 **********
      const pdfDpi = 72;
      const mmPerInch = 25.4;
      const pxPerMM = (renderScale * pdfDpi) / mmPerInch;
      
      // 转换毫米单位为像素
      const topMarginPx = Math.round(top_margin * pxPerMM);
      const bottomMarginPx = Math.round(bottom_margin * pxPerMM);
      const textSafetyMarginPx = Math.round(textSafetyMargin * pxPerMM);

      // ********** 关键2：文字边界精确检测 **********
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity; // 文字顶部边界
      let maxY = -Infinity; // 文字底部边界
      let hasText = false;

      // 遍历所有文字元素
      textContent.items.forEach(item => {
        if (!item.str.trim()) return; // 跳过空白
        
        hasText = true;
        const x = item.transform[4] * renderScale;
        const y = item.transform[5] * renderScale;
        const width = item.width * renderScale;
        const height = item.height * renderScale;
        
        // 转换为常规坐标系（顶部为0）
        const canvasY = canvas.height - y;
        const textTop = canvasY - height;
        const textBottom = canvasY;
        
        // 更新边界
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x + width);
        minY = Math.min(minY, textTop);
        maxY = Math.max(maxY, textBottom);
      });

      // 无文字时使用整个页面
      if (!hasText) {
        minX = 0;
        maxX = canvas.width;
        minY = 0;
        maxY = canvas.height;
      }

      // 添加安全距离
      minX = Math.max(0, minX - textSafetyMarginPx);
      maxX = Math.min(canvas.width, maxX + textSafetyMarginPx);
      minY = Math.max(0, minY - textSafetyMarginPx);
      maxY = Math.min(canvas.height, maxY + textSafetyMarginPx);

      // 文字内容实际尺寸
      const textWidth = maxX - minX;
      const textHeight = maxY - minY;

      // ********** 关键3：固定分辨率画布处理 **********
      const outputCanvas = document.createElement('canvas');
      outputCanvas.width = targetWidth;
      outputCanvas.height = targetHeight;
      const outputCtx = outputCanvas.getContext('2d');

      // 填充白色背景
      outputCtx.fillStyle = 'white';
      outputCtx.fillRect(0, 0, targetWidth, targetHeight);

      // ********** 关键4：按固定尺寸绘制，确保内容完整 **********
      // 计算可用内容区域（扣除上下留白）
      const contentAreaHeight = targetHeight - topMarginPx - bottomMarginPx;
      
      // 计算缩放比例（确保内容能放入可用区域）
      const scaleX = targetWidth / textWidth;
      const scaleY = contentAreaHeight / textHeight;
      const scale = Math.min(scaleX, scaleY); // 取最小比例保证内容完整

      // 计算绘制位置和尺寸
      const drawWidth = textWidth * scale;
      const drawHeight = textHeight * scale;
      const offsetX = (targetWidth - drawWidth) / 2; // 水平居中
      const offsetY = topMarginPx; // 顶部留白后开始绘制

      // 绘制内容（确保完整显示）
      outputCtx.drawImage(
        canvas,
        minX, minY,          // 源区域：包含所有文字
        textWidth, textHeight, // 源区域尺寸
        offsetX, offsetY,    // 目标位置：顶部留6mm，水平居中
        drawWidth, drawHeight // 目标尺寸：不拉伸
      );

      // 生成图片URL
      const imageUrl = outputCanvas.toDataURL('image/jpeg', 0.95);

      // 分类存储页面图片
      if (answerStartPage && i >= answerStartPage) {
        answerPages.push(imageUrl);
      } else {
        const linesFromPage = extractLinesFromPdfPage(textContent);
        allLines = allLines.concat(linesFromPage);
        mainPages.push(imageUrl);
      }

      canvas.remove();
      outputCanvas.remove();
    }

    // 处理文本内容
    htmlContent = allLines.map(line => `<p>${line}</p>`).join('');

	console.log("htmlContent:"+htmlContent);
    const { scoresList, questionType, scoresList2 } = extractScores(htmlContent, title);
    const mergedScore = mergeScores(scoresList, scoresList2);

    return {
      mainPages,
      answerPages,
      scores: mergedScore,
      questionType,
      title
    };

  } catch (error) {
    throw new Error('PDF文档处理失败：' + error.message);
  }
};




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

  //console.log(tt[0]+','+tt[2]);
  console.log("0.tt:"+tt);
  if (tt[0] === '2' && tt[2] > 2) {
    //tt = '2,2'
  }
  console.log("1.tt:"+tt);
  if ((tt[0] === '3' || tt[0] === '4') && tt[2] > 3) {
    //tt = '3,3'
  }
  console.log("2.tt:"+tt);

  const mapping = {
    '1,1': 1,
	'1,2': 1,
	'1,3': 1,
    '2,1': 2,	
    '3,2': 3,
    '4,2': 4,
    '2,2': 5,
    '3,3': 4,
	'3,4': 4,
    '4,3': 7,
	'4,4': 4
  };
  return mapping[tt] || 2;
}
