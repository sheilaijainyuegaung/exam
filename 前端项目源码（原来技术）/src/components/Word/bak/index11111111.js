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
    /.*[单元月中期末]考.*/
  ]

  let title = ''

  // 查找符合标题特征的文本
  for (const line of lines) {
    const text = line.text.trim()
	//console.log("for line.text:"+text);
    // 检查文本长度是否在合理范围内
    if (text.length >= 5 && text.length <= 50) {			
		//console.log("text.length >= 5 && text.length <= 50,"+text);
      // 检查是否匹配标题模式
      if (titlePatterns.some(pattern => pattern.test(text))) {
        title = text
        break
      }
    }
  }
  // 如果没有找到符合特征的标题，使用第一行文本（长度合适的）
  if (!title) {
	//console.log("没有标题");
    for (const line of lines) {
      const text = line.text.trim()
	  //console.log("line.text:"+text);
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


  //console.log("extractScores htmlContent:"+htmlContent);
  //console.log("extractScores title:"+title); 

  // 定义标题匹配模式
  const maxLevel = 3

  // 分值提取正则（全局匹配）
  let scorePattern = /[（(]\s*(?:共)?\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/g;
  let scorePattern2 = /[（(]\s*(?:共)?\s*(?!\d+\s*[）)])(?:\d+(?:\.\d+)?\s*分|)\s*[）)]/g;
  //const singleScorePattern = /[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/;

  //const singleScorePattern = /[（(]\s*(\d+(?:\.\d+)?)\s*(分)?\s*[）)]/; //匹配空白括号
  //const singleScorePattern = /[（(]\s*(?!(?:\d+(?:\.\d+)?)\s*[）)])(?:(\d+(?:\.\d+)?)\s*分\s*|)\s*[）)]/;
  const singleScorePattern = /[（(]\s*(?:共\s*)?(?:(\d+(?:\.\d+)?)\s*分\s*|)\s*[）)]/;

  //const singleScorePattern = /[（(][\s\S]*?(\d+(?:\.\d+)?)\s*分[\s\S]*?[）)]/;
  //const scorePattern = /[（(][\s　]*共[\s　]*(\d+(?:\.\d+)?)\s*分\s*[）)]/g;
  //const singleScorePattern = /[（(][\s　]*共[\s　]*(\d+(?:\.\d+)?)\s*分\s*[）)]/;

  // 移除所有图片标签和空白字符
  let contentWithoutImages = htmlContent.replace(/<img[^>]*>/g, '').replace(/（/g, '(').replace(/）/g, ')').replace(/\s+/g, '').trim();
  //console.log("0.contentWithoutImages:"+contentWithoutImages);


  if (title) {
    contentWithoutImages = contentWithoutImages.split(title.replace(/\s+/g, '').replace(/（/g, '(').replace(/）/g, ')').trim())[1]
  }



  // 判断试卷是什么类型
  const templateType = getTemplateType(contentWithoutImages);

  //console.log("templateType:"+templateType);
  console.log("contentWithoutImages::"+contentWithoutImages);

  // 构建文本树
   const textTree = processText(contentWithoutImages);
   const textTree2 = processText2(contentWithoutImages);

   //console.log("start textTree:"+JSON.stringify(textTree)); 	
   //console.log("start textTree2:"+JSON.stringify(textTree2)); 	


	//const textTree = [[{"text":"看拼音写词语(16分)</p><p>(1)hétān()</p><p>(5)chànà()</p><p>(2)yíduàn()</p><p>(6)xiāngbiān()</p><p>(3)fànwéi()</p><p>(7)bùjǐn()</p><p>(4)kuòdà()</p><p>(8)zǐsè()</p>","score":1,"childText":[{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]}]},{"text":"形近字组词(8分)</p><p>(1)镶()</p><p>(5)壤()</p><p>(2)努()</p><p>(6)怒()</p><p>(3)烂()</p><p>(7)拦()</p><p>(4)替()</p><p>(8)剃()</p>","score":1,"childText":[{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]}]},{"text":"选择正确读音(6分)</p><p>(1)太阳好像负着重荷(héhè)似的。</p><p>(2)一刹那(chàshà)间，这个深红的圆东西，忽然发出了夺</p><p>目的亮光。</p><p>第1页</p>","score":6,"childText":[]}]];


	//const textTree = [[{"text":"看拼音写词语(16分)</p><p>(1)hétān()</p><p>(5)chànà()</p><p>(2)yíduàn()</p><p>(6)xiāngbiān()</p><p>(3)fànwéi()</p><p>(7)bùjǐn()</p><p>(4)kuòdà()</p><p>(8)zǐsè()</p>","score":16,"childText":[{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]},{"text":"(1分)","score":1,"childText":[]}]},{"text":"形近字组词(8分)</p><p>(1)镶()</p><p>(5)壤()</p><p>(2)努()</p><p>(6)怒()</p><p>(3)烂()</p><p>(7)拦()</p><p>(4)替()</p><p>(8)剃()</p>","score":8,"childText":[]},{"text":"选择正确读音(6分)</p><p>(1)太阳好像负着重荷(héhè)似的。</p><p>(2)一刹那(chàshà)间，这个深红的圆东西，忽然发出了夺</p><p>目的亮光。</p><p>第1页</p>","score":6,"childText":[]}]];


  // 提取分值信息
  const scoresList = extractScoreInfo(textTree);


 	

  // 提取分值信息
  const scoresList2 = extractScoreInfo2(textTree2);


  //console.log("*****scoresList2:"+JSON.stringify(scoresList2)); 

  const treeDepth = getTreeDepth(scoresList);

  //console.log("treeDepth:"+treeDepth); 

  const questionType = getQuestionType(templateType, treeDepth);
  //console.log("questionType:"+questionType); 
	
  
  // 递归处理文本，构建树结构
  function processText(text, level = 0, prevCounter = 0) {	
	//console.log("-------processText text:"+text);
	//text = text.replace(/^<\/p>/, '');
    const fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接

    if (!fixedText || fixedText.length === 0) {
		//console.log("!fixedText or fixedText.length === 0");
		return null;	
	}else{
		//console.log("fixedText and fixedText.length > 0");
	}

    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {
		//console.log("level:"+level + ", maxLevel:" + maxLevel );
		//console.log("查找所有分值scorePattern:" + scorePattern );
		//console.log("查找所有分值fixedText:" + fixedText );

      // 查找所有分值
      const scores = Array.from(fixedText.matchAll(scorePattern)).map(match => parseFloat(match[1]));	    
	  //console.log("查找所有分值processText scores:"+JSON.stringify(scores)); 

      // 如果有多个分值，创建子节点
      if (scores.length > 1) {
		// 跳过第一个总分值（8分），从第二个分值开始
        const childScores = scores.slice(1);
		//console.log("scores.length>1:"+JSON.stringify(childScores)); 
		//console.log("scores.length>1 score:" +  scores.reduce((a, b) => a + b, 0)); 
		let score_tmp = scores.reduce((a, b) => a + b, 0); 

        return {
          text: fixedText,
          score: score_tmp==NaN?0:score_tmp,
          childText: childScores.map(score => ({
            text: score_tmp==NaN?0:`(${score}分)`,
            score: score_tmp==NaN?0:score,
            childText: []
          }))
        };


      } else {
        // 单个分值的情况
        const scoreMatch = fixedText.match(singleScorePattern);
		//console.log("单个分值的情况fixedText:"+fixedText);
		//console.log("单个分值的情况scoreMatch:"+JSON.stringify(scoreMatch)); 

		if(JSON.stringify(scoreMatch)=='()' || JSON.stringify(scoreMatch)=='()'){

				return {
				  text: '',
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

    let segments = [];
    let tempText = text;

	//console.log("***tempText:"+tempText); 
    // 根据不同的模式类型使用不同的匹配逻辑
    if (level === 0) { // 中文数字标题
      // 按照 chineseNoRegs 数组顺序尝试匹配
      for (let i = 0; i < chineseNoRegs.length; i++) {
        const pattern = chineseNoRegs[i];
        const match = tempText.match(pattern);
        if (!match) {

			//console.log("0.tempText:"+tempText); 

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
          //pattern = new RegExp(`(?<!<td\\s*>)<p>${counter}[.．、]`);
		  pattern = new RegExp(`(?:<p>)?${counter}[.．、]\\(?\\d+分\\)?`);

        } else {
          pattern = new RegExp(`\\(${counter}?\\)`);

        }
        const match = tempText.match(pattern);
        if (!match) {	
			//console.log("没有匹配到!match:"); 

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

    for (let i = 1; i < segments.length; i++) {
      const segment = segments[i].trim();
      if (segment) {
		  const node = processText(segment, level + 1, counterSeries.reduce((a, b) => a + b, 0));
        if (node) {
			//console.log(" if 2.node:"+JSON.stringify(node)); 
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
	



	// 递归处理文本，构建树结构
  function processText2(text, level = 0, prevCounter = 0) {	
	//console.log("-------processText2 text:"+text);
    const fixedText = text.replace(/\((\d+)<\/p><p>分\)/g, '($1分)');//将断行的分数进行连接
    if (!fixedText || fixedText.length === 0) {
		//console.log("!fixedText or fixedText.length === 0");
		return null;	
	}else{
		//console.log("fixedText and fixedText.length > 0");
	}

	//console.log("fixedText:"+fixedText);

    // 如果已经没有可用的分割模式，返回文本本身
    if (level >= maxLevel) {	

      // 查找所有分值
      const scores = Array.from(fixedText.matchAll(scorePattern2))
        .map(match => parseFloat(match[1]));
	  
	  
	  //console.log("processText2 scores:"+JSON.stringify(scores)); 

      // 如果有多个分值，创建子节点
      if (scores.length > 1) {
		// 跳过第一个总分值（8分），从第二个分值开始
        const childScores = scores.slice(1);

		let score_tmp = scores.reduce((a, b) => a + b, 0); 
		
	
        return {
          text: isNaN(score_tmp)?`(0分)`:`(${score}分)`,
          score: isNaN(score_tmp)?0:score_tmp,
          childText: childScores.map(score => ({
            text: isNaN(score_tmp)?`(0分)`:`(${score}分)`,
            score: isNaN(score_tmp)?0:score,
            childText: []
          }))
        };
		

	/*
		return {
          text: fixedText,
          score: scores.reduce((a, b) => a + b, 0), // 使用第一个分值作为总分
          childText: childScores.map(score => ({
            text: `(${score}分)`,
            score: score,
            childText: []
          }))
        };*/


      } else {

        // 单个分值的情况
        const scoreMatch = fixedText.match(singleScorePattern);
		//console.log("单个分值的情况fixedText:"+fixedText);
		//console.log("单个分值的情况scoreMatch:"+JSON.stringify(scoreMatch)); 

		if(JSON.stringify(scoreMatch)=='()' || JSON.stringify(scoreMatch)=='()'){
			

			//console.log("return (0分)");

				return {
				  text: `(0分)`,
				  score: 0,
				  childText: []
				}

		}else{

			const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0;
			// 如果分值为0，返回null



			//console.log("return " + fixedText + "(" + score + "分)");

			return score > 0 ? {
			  text: fixedText,
			  score: score,
			  childText: []
			} :null;
		}
      }
    }

    let segments = [];
    let tempText = text;

	//console.log("***tempText:"+tempText); 

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
      return processText2(text, level + 1);
    }

    return result;
  }



   // 提取分值信息
  function extractScoreInfo(node, parent = null, grandParent = null, siblings = [], parentSiblings = []) {
    if (!node) return null;

	//console.log("***extractScoreInfo node:"+JSON.stringify(node)); 


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
      return '';
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
      childScores: finalChildScores.length > 0 ? finalChildScores : []
    };




  }//extractScoreInfo2


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
	scoresList2,
  };

}




export const processHtmlContent = async (htmlContent) => {
  try {
    const mainPagesList = []
    const answerPagesList = []


	//console.log("processHtmlContent htmlContent:"+htmlContent);

    // 获取试卷标题，第一个strong标签包裹的内容
    const title = htmlContent.match(/<strong>(.*?)<\/strong>/)[1]


	//console.log("processHtmlContent title:"+title);

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
			const mainContent = splitContent[0];
			const answerContent =  '';
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
	//console.log("firstPageText:"+firstPageText);	
    const title = extractPdfTitle(firstPageText);
	//console.log("handlePdfDocument title:"+title);

    for (let i = 1; i <= totalPages; i++) {
      const page = await pdf.getPage(i)
      const textContent = await page.getTextContent()
      const pageText = textContent.items.map(item => item.str).join(' ')
	  
	  //console.log(i+" pageText:"+pageText);
      //const answerPattern = /(^|\s|[。．.、\n])(参考)?答案($|\s|[：:．.、\n])/g
	  // 修改后的正则表达式
	  const answerPattern = /(^|\s|[。．.、\n(（])(参考)?答案(页)?($|\s|[：:．.、\n)）])/g;

      if (answerPattern.test(pageText) && !answerStartPage) {
        answerStartPage = i
		//console.log("answerStartPage:"+i);
      }

      const viewport = page.getViewport({ scale: 3.0 })
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      canvas.height = viewport.height
      canvas.width = viewport.width
		
	 // 第一步：使用更高的分辨率渲染（提升清晰度基础）
      await page.render({
        canvasContext: context,
        viewport: viewport
      }).promise



	// 第二步：创建临时Canvas进行颜色处理
	const tempCanvas = document.createElement('canvas');
	tempCanvas.width = canvas.width;
	tempCanvas.height = canvas.height;
	const tempCtx = tempCanvas.getContext('2d');

	// 第三步：应用颜色增强处理（加深文字）
	tempCtx.drawImage(canvas, 0, 0);

	// 方法1：使用图像滤镜增强对比度（现代浏览器支持）
	if (typeof tempCtx.filter !== 'undefined') {

		//console.log("tempCtx.filter: !undefined");
		// 在颜色加深后添加锐化
		//tempCtx.filter = 'contrast(1.8) brightness(0.8)';
		tempCtx.filter = 'contrast(1.9) saturate(1.1)';
		//tempCtx.drawImage(canvas, 0, 0);
		tempCtx.drawImage(canvas, 0, 0); // 重新绘制应用滤镜
		tempCtx.filter = 'none'; // 重置滤镜避免影响后续操作

	} 
	// 方法2：手动处理像素（兼容所有浏览器）
	else {
	  const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
	  const data = imageData.data;
	  
	  // 加深文字处理：将深色像素变得更黑，浅色像素变得更白
	  for (let i = 0; i < data.length; i += 4) {
		const r = data[i];
		const g = data[i + 1];
		const b = data[i + 2];
		const avg = (r + g + b) / 3;
		
		//console.log("avg:"+avg);

		// 如果是文字等深色内容（灰度值低于阈值）
		if (avg < 200) {
		  // 加深处理：将颜色值降低（更黑）
		  const darknessFactor = 0.7; // 加深程度（0-1，越小越黑）
		  data[i] = r * darknessFactor;
		  data[i + 1] = g * darknessFactor;
		  data[i + 2] = b * darknessFactor;
		}
	  }
	  tempCtx.putImageData(imageData, 0, 0);
	}

	  // 计算留白像素值（假设PDF是标准A4尺寸：210mm×297mm）
	  const pdfWidthMM = 210;   // A4宽度210mm
	  const pdfHeightMM = 297;  // A4高度297mm

	  // 计算毫米到像素的转换比例
	  const pxPerMMWidth = tempCanvas.width / pdfWidthMM;   // 宽度方向每毫米像素数
	  const pxPerMMHeight = tempCanvas.height / pdfHeightMM; // 高度方向每毫米像素数
     
    // 定义留白大小
    const topMarginPx = 6 * pxPerMMHeight;    // 上留白6mm
    const sideMarginPx = 2 * pxPerMMWidth;    // 左右留白2mm
    const bottomMarginPx = 2 * pxPerMMHeight; // 下留白2mm

    // 创建新Canvas用于裁切后的图像
    const outputCanvas = document.createElement('canvas');
	outputCanvas.width = 2692;  // 目标宽度
    outputCanvas.height = 3744; // 目标高度
    const outputCtx = outputCanvas.getContext('2d');


    // 绘制图像到新Canvas，考虑留白
    //outputCtx.drawImage(canvas, sideMarginPx, topMarginPx, canvas.width - 2 * sideMarginPx, canvas.height - topMarginPx - bottomMarginPx); 
   // 检查是否不满一页（这里需要根据实际内容判断）
    // 假设有一个函数isContentFullPage()来判断是否满页
    // 如果没有，可以使用简单的启发式方法，比如检测底部是否有足够内容
    const isFullPage = checkIfPageIsFull(tempCtx, tempCanvas); // 需要实现这个函数

		// 计算裁切区域
		let cropX, cropY, cropWidth, cropHeight;

		if (isFullPage) {
		  // 满页：按所有留白裁切
		  cropX = sideMarginPx;
		  cropY = topMarginPx;
		  cropWidth = tempCanvas.width - (2 * sideMarginPx);
		  cropHeight = tempCanvas.height - topMarginPx - bottomMarginPx;
		} else {
		  // 不满页：只保留上留白
		  cropX = 0;
		  cropY = topMarginPx;
		  cropWidth = tempCanvas.width;
		  cropHeight = tempCanvas.height - topMarginPx;
		}

		// 计算缩放比例（保持宽高比）
		const targetAspectRatio = 2692 / 3744; // 目标宽高比
		const sourceAspectRatio = cropWidth / cropHeight; // 源宽高比

		let scale, drawWidth, drawHeight, offsetX, offsetY;

		if (sourceAspectRatio > targetAspectRatio) {
		  // 源图像比目标更宽，以宽度为基准缩放
		  scale = outputCanvas.width / cropWidth;
		  drawWidth = outputCanvas.width;
		  drawHeight = cropHeight * scale;
		  offsetX = 0;
		  offsetY = (outputCanvas.height - drawHeight) / 2;
		} else {
		  // 源图像比目标更高，以高度为基准缩放
		  scale = outputCanvas.height / cropHeight;
		  drawHeight = outputCanvas.height;
		  drawWidth = cropWidth * scale;
		  offsetX = (outputCanvas.width - drawWidth) / 2;
		  offsetY = 0;
		}

		// 填充白色背景
		outputCtx.fillStyle = 'white';
		outputCtx.fillRect(0, 0, outputCanvas.width, outputCanvas.height);

		// 绘制裁切并缩放的图像
		outputCtx.drawImage(
		  tempCanvas,
		  cropX, cropY, cropWidth, cropHeight,  // 源图像裁切区域
		  offsetX, offsetY, drawWidth, drawHeight // 目标绘制区域
		);

		const imageUrl = outputCanvas.toDataURL('image/jpeg', 1);



      //const imageUrl = canvas.toDataURL('image/jpeg', 0.9)
      if (answerStartPage && i >= answerStartPage) {
        answerPages.push(imageUrl)
      } else {
        // 使用新函数提取行，并添加到 allLines 数组
        const linesFromPage = extractLinesFromPdfPage(textContent);
        allLines = allLines.concat(linesFromPage);
        mainPages.push(imageUrl)
      }


	

	




      // 辅助函数：检测页面是否满页（需要根据实际情况调整）
    function checkIfPageIsFull(ctx, canvas) {
      // 简单实现：检查底部区域是否有足够内容
      const bottomRegionHeight = 100; // 检查底部100像素区域
      const imageData = ctx.getImageData(
        0, 
        canvas.height - bottomRegionHeight, 
        canvas.width, 
        bottomRegionHeight
      );
      
      // 计算非白色像素比例
      let nonWhitePixels = 0;
      const data = imageData.data;
      for (let i = 0; i < data.length; i += 4) {
        // 简单的白色检测：RGB都大于240
        if (data[i] < 240 || data[i+1] < 240 || data[i+2] < 240) {
          nonWhitePixels++;
        }
      }
      
      // 如果非白色像素超过一定阈值，认为有内容
      const threshold = 0.05; // 5%的阈值
      return (nonWhitePixels / (canvas.width * bottomRegionHeight)) > threshold;
    }

      canvas.remove()

    }

    // 将所有行合并为一个字符串，用换行符分隔，每一行头部添加<p>
    htmlContent = allLines.map(line => `<p>${line}</p>`).join('');

	//**********************************重要返回************************************
	

    const { scoresList, questionType , scoresList2 } = extractScores(htmlContent, title)

	// 合并分数
	const mergedScore = mergeScores(scoresList, scoresList2);


    return {
      mainPages,
      answerPages,
      scores: mergedScore,
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

  //console.log(tt[0]+','+tt[2]);
  //console.log("tt:"+tt);

  if (tt[0] === '2' && tt[2] > 2) {
    tt = '2,2'
  }
  if ((tt[0] === '3' || tt[0] === '4') && tt[2] > 3) {
    tt = '3,3'
  }

  const mapping = {
    '1,1': 1,
	'1,2': 1,
	'1,3': 1,
    '2,1': 2,	
    '3,2': 3,
    '4,2': 4,
    '2,2': 5,
    '3,3': 6,
    '4,3': 7
  };
  return mapping[tt] || 2;
}
