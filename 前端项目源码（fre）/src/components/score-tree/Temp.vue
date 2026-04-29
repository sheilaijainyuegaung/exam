<template>
  <div :class="`score-node ${isLevel3(node.childScores)}`">
    <div class="row">
      <span :class="'index ' + hasSelLevel()" @click="onSel" @dblclick="onAvgScore">{{ prefix() }}</span>
      <span v-if="hasChildren()" class="score">
        {{ calcScore(node) }}分
      </span>
      <div v-else class="leaf-input">
        <input
          class="score-input"
          type="text"
          :value="node.score"
          @input="onInput($event, node)"
        />
      </div>
    </div>
    <div v-if="hasChildren()" :class="`children ${isLevel3(node.childScores)}`">
      <ScoreNode
        v-for="(child,index) in node.childScores"
        :key="index"
        :index="index"
        :node="child"
        :id="`${id}-${level+1}-${index}`"
        :order="order"
        :parent="node"
        :selId="selId"
        :level="level + 1"
        :selItem="selItem"
        :config="config"
      />
    </div>
  </div>
</template>

<script>
import { calcScore, isLevel3, getTopicNum, numToChinese } from "./temp";

export default {
  name: "ScoreNode",
  props: {
    level: Number,
    node: Object,
    parent: Object,
    index: Number,
    order: Number,
    id: String,
    selId: String,
    config: {},
    selItem: {
      type: Function,
      default: (item, parent, selId) => {
        console.log("默认选择:", item, parent, selId);
      },
    },
  },
  methods: {
    isLevel3,
    calcScore,
    getId() {
      return this.id;
    },
    onAvgScore() {
      if (!this.hasChildren()) {
        return;
      }
      this.$prompt("请输入要分配的分值", "平均赋分给子级", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        inputPattern: /^\d+(\.\d+)?$/,
        inputErrorMessage: "请输入数字",
      })
        .then(({ value }) => {
          console.log("输入值:", value);
          let size = this.node.childScores.length;
          let avg = Number(value) / size;
          this.node.childScores.forEach((item) => {
            item.score = avg;
          });
        })
        .catch(() => {
          console.log("取消输入");
        });
    },
    onSel() {
      let isSel = this.getId() === this.selId;
      this.selItem(this.node, this.parent, isSel ? "" : this.getId());
    },
    hasSelLevel() {
      let isSel = this.getId() === this.selId;
      return isSel ? "selLevel" : "";
    },
    hasChildren() {
      return this.node.childScores && this.node.childScores.length > 0;
    },
    prefix() {
      if (this.parent?.type === 2) {
        return "";
      }
      let index = this.index + 1;
      const { type } = this.config;
      if (type === 3 || type === 4) {
        if (type === 4 && this.level === 2) {
          console.log("总数:", this.order);
          index += this.order;
        }
        const map = {
          1: () => numToChinese(index),
          2: () => index,
          3: () => `(${index})`,
          default: () => getTopicNum(index),
        };
        return (map[this.level] || map.default)() + ".";
      }
      if (type === 2 && this.level === 2) {
        index += this.order;
      }
      const map = {
        1: () => `${index}`,
        2: () => `(${index})`,
        default: () => getTopicNum(index),
      };
      return (map[this.level] || map.default)() + ".";
    },
    onInput(e, node) {
      let val = e.target.value.trim();
      if (val.length > 4) {
        val = val.slice(0, 4);
      }
      if (!/^\d*\.?\d*$/.test(val)) {
        e.target.value = node.score;
        return;
      }
      const num = Number(val);
      if (val !== "" && (isNaN(num) || num > 100)) {
        e.target.value = node.score;
        return;
      }
      node.score = val === "" ? 0 : num;
    },
  },
};
</script>

<style scoped lang="scss">
.layout {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
}

.score-node {
  margin-left: 8px;
}

.index,
.score {
  cursor: pointer;
  color: black;
}

.index:hover {
  text-decoration: underline;
}

.children {
  margin-left: 8px;
  display: contents;
}

.row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  line-height: 28px;
}

.score-input {
  width: 50px;
  border: none;
  border-bottom: 1px solid #333;
  outline: none;
  font-size: 13px;
  text-align: center;
  padding: 2px 4px;
  background: transparent;
}

.score-input:focus {
  border-bottom: 1px solid #409eff;
}

.selLevel {
  background: orange;
}
</style>
