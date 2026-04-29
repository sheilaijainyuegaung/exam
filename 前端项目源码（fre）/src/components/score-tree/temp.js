export const calcScore = (node) => {
  if (!node.childScores || node.childScores.length === 0) {
    return Number(node.score) || 0;
  }
  return node.childScores.reduce((sum, child) => {
    return sum + calcScore(child);
  }, 0);
};

export const calcTotalScore = (list) => {
  return list.reduce((sum, item) => {
    return sum + calcScore(item);
  }, 0);
};

export const hasLevel = (list = []) => {
  return list.some(
    (level1) => Array.isArray(level1.childScores) && level1.childScores.length > 0
  );
};

export const isLevel3 = (list) => {
  return hasLevel(list) ? "" : "layout";
};

export const getTopicNum = (index) => {
  const circleNumberMap = new Map([
    [1, "①"], [2, "②"], [3, "③"],
    [4, "④"], [5, "⑤"], [6, "⑥"],
    [7, "⑦"], [8, "⑧"], [9, "⑨"],
    [10, "⑩"], [11, "⑪"], [12, "⑫"],
    [13, "⑬"], [14, "⑭"], [15, "⑮"],
    [16, "⑯"], [17, "⑰"], [18, "⑱"],
    [19, "⑲"], [20, "⑳"], [21, "㉑"],
    [22, "㉒"], [23, "㉓"], [24, "㉔"],
    [25, "㉕"], [26, "㉖"], [27, "㉗"],
    [28, "㉘"], [29, "㉙"], [30, "㉚"],
  ]);
  return circleNumberMap.get(index) ?? `${index + 1}`;
};

export const numToChinese = (num) => {
  const map = {
    0: "",
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
    10: "十",
  };
  if (num <= 10) {
    return map[num];
  } else if (num < 20) {
    return "十" + map[num % 10];
  } else {
    const tens = Math.floor(num / 10);
    const ones = num % 10;
    return map[tens] + "十" + map[ones];
  }
};
