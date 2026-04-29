<template>
  <div :class="`score-node ${isLevel3(node.childScores)}`">
    <div class="row">
      <span class="index" :class="hasSelLevel()" @click="onSel" @dblclick="onAvgScore">
        {{ prefix() }}
      </span>
      <span v-if="hasChildren()" class="score">{{ calcScore(node) }}分</span>
      <div v-else class="leaf-input">
        <input class="score-input" type="text" :value="node.score" @input="onInput($event, node)">
      </div>
    </div>

    <div v-if="hasChildren()" :class="`children ${isLevel3(node.childScores)}`">
      <ScoreNode
        v-for="(child, index) in node.childScores"
        :key="`${id}-${level + 1}-${index}`"
        :index="index"
        :node="child"
        :id="`${id}-${level + 1}-${index}`"
        :order="order"
        :parent="node"
        :selId="selId"
        :level="level + 1"
        :selItem="selItem"
        :config="config"
        :onChanged="onChanged"
      />
    </div>
  </div>
</template>

<script>
import { calcScore, getTopicNum, isLevel3, numToChinese } from "./util";

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
    config: Object,
    selItem: {
      type: Function,
      default: () => {},
    },
    onChanged: {
      type: Function,
      default: () => {},
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
      if (typeof this.$prompt === "function") {
        this.$prompt("请输入要分配的分值", "平均赋分给子级", {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          inputPattern: /^\d+(\.\d+)?$/,
          inputErrorMessage: "请输入数字",
        })
          .then(({ value }) => {
            const size = this.node.childScores.length || 1;
            const avg = Number(value) / size;
            this.node.childScores.forEach((item) => {
              item.score = avg;
            });
            this.onChanged();
          })
          .catch(() => {});
        return;
      }

      const raw = window.prompt("请输入要分配的分值", String(this.calcScore(this.node) || 0));
      if (raw === null) {
        return;
      }
      const total = Number(raw);
      if (!Number.isFinite(total) || total < 0) {
        return;
      }
      const size = this.node.childScores.length || 1;
      const avg = total / size;
      this.node.childScores.forEach((item) => {
        item.score = avg;
      });
      this.onChanged();
    },
    onSel() {
      const isSel = this.getId() === this.selId;
      this.selItem(this.node, this.parent, isSel ? "" : this.getId());
    },
    hasSelLevel() {
      return this.getId() === this.selId ? "selLevel" : "";
    },
    hasChildren() {
      return Array.isArray(this.node.childScores) && this.node.childScores.length > 0;
    },
    prefix() {
      if (this.parent && this.parent.type === 2) {
        return "";
      }
      let index = this.index + 1;
      const type = Number(this.config && this.config.type) || 1;

      if (type === 3 || type === 4) {
        if (type === 4 && this.level === 2) {
          index += this.order || 0;
        }
        const map = {
          1: () => numToChinese(index),
          2: () => `${index}`,
          3: () => `(${index})`,
          default: () => getTopicNum(index),
        };
        return `${(map[this.level] || map.default)()}.`;
      }

      if (type === 2 && this.level === 2) {
        index += this.order || 0;
      }

      const map = {
        1: () => `${index}`,
        2: () => `(${index})`,
        default: () => getTopicNum(index),
      };
      return `${(map[this.level] || map.default)()}.`;
    },
    onInput(e, node) {
      let val = String(e.target.value || "").trim();
      if (val.length > 6) {
        val = val.slice(0, 6);
      }
      if (!/^\d*\.?\d*$/.test(val)) {
        e.target.value = node.score;
        return;
      }
      const num = Number(val);
      if (val !== "" && (!Number.isFinite(num) || num > 1000)) {
        e.target.value = node.score;
        return;
      }
      node.score = val === "" ? 0 : num;
      this.onChanged();
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
  color: #111;
  font-size: 14px;
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
  line-height: 24px;
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
  background: #ffb74d;
}
</style>
