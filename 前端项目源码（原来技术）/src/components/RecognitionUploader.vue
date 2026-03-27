<template>
  <div class="recognition-uploader">
    <div class="row">
      <label>上传试卷文件</label>
      <input
        class="file-input"
        type="file"
        accept=".doc,.docx,.pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf"
        multiple
        @change="onFileChange"
      >
    </div>

    <div v-if="selectedFiles.length > 0" class="row file-list-row">
      <label></label>
      <div class="selected-files">
        <span class="file-tag" v-for="(item, idx) in selectedFiles" :key="`${item.name}-${idx}`">
          {{ item.name }}
        </span>
      </div>
    </div>

    <div class="row">
      <label>规则模板</label>
      <select v-model="ruleProfileId" class="select">
        <option value="">默认规则</option>
        <option v-for="item in ruleProfiles" :key="item.id" :value="item.id">
          {{ item.name }}
        </option>
      </select>
    </div>

    <div class="row">
      <label>文档排版</label>
      <button class="config-btn" type="button" @click="openLayoutModal">文档排版调整</button>
      <span class="hint">{{ layoutSummaryText }}</span>
    </div>

    <div class="row">
      <button class="btn" :disabled="uploading || selectedFiles.length === 0" @click="submitUpload">
        {{ uploading ? "上传中..." : "开始识别" }}
      </button>
      <span class="hint">支持 doc/docx/pdf，多文件异步任务处理</span>
    </div>

    <div v-if="errorMessage" class="error">{{ errorMessage }}</div>

    <div class="history-header">
      <span>提取记录</span>
      <button class="refresh-btn" :disabled="loadingHistory" @click="refreshTaskHistory">
        {{ loadingHistory ? "刷新中..." : "刷新" }}
      </button>
    </div>

    <div v-if="historyItems.length === 0" class="empty">暂无提取记录</div>

    <div v-else class="task-list">
      <div class="task-item" v-for="item in historyItems" :key="item.taskId">
        <div class="task-main">
          <div class="task-file">{{ item.fileName }}</div>
          <div class="task-meta">
            任务 {{ item.taskId }} · {{ getTaskState(item.taskId).status }} · {{ getTaskState(item.taskId).progress }}%
          </div>
          <div v-if="getTaskState(item.taskId).errorMessage" class="task-error">
            {{ getTaskState(item.taskId).errorMessage }}
          </div>
        </div>
        <button
          class="view-btn"
          :disabled="viewingTaskId === item.taskId"
          @click="viewTask(item.taskId)"
        >
          {{ viewingTaskId === item.taskId ? "加载中..." : "查看结果" }}
        </button>
      </div>
    </div>

    <div v-if="showLayoutModal" class="layout-modal-mask" @click.self="closeLayoutModal">
      <div class="layout-modal">
        <div class="layout-modal-title">文档排版调整（仅影响预览 PDF）</div>
        <div class="layout-grid">
          <div class="layout-field" v-for="field in layoutFieldDefs" :key="field.key">
            <label :for="`layout-${field.key}`">{{ field.label }}</label>
            <input
              :id="`layout-${field.key}`"
              v-model.trim="layoutDraft[field.key]"
              class="layout-input"
              type="number"
              :step="field.step"
              :min="field.min"
              :max="field.max"
            >
          </div>
        </div>
        <div class="layout-actions">
          <button type="button" class="modal-btn light" @click="resetLayoutDraft">清空</button>
          <button type="button" class="modal-btn light" @click="closeLayoutModal">取消</button>
          <button type="button" class="modal-btn primary" @click="applyLayoutModal">应用</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {
  getTaskDetails,
  getTaskResult,
  getTaskStatus,
  listRecognitionTasks,
  listRuleProfiles,
  uploadExamFiles,
} from "@/services/recognitionApi";

const LAYOUT_FIELD_DEFS = [
  { key: "marginTopCm", label: "上边距(cm)", min: 0, max: 10, step: 0.1 },
  { key: "marginRightCm", label: "右边距(cm)", min: 0, max: 10, step: 0.1 },
  { key: "marginBottomCm", label: "下边距(cm)", min: 0, max: 10, step: 0.1 },
  { key: "marginLeftCm", label: "左边距(cm)", min: 0, max: 10, step: 0.1 },
  { key: "paragraphLeftIndentCm", label: "段落左缩进(cm)", min: 0, max: 10, step: 0.1 },
  { key: "paragraphRightIndentCm", label: "段落右缩进(cm)", min: 0, max: 10, step: 0.1 },
  { key: "firstLineIndentCm", label: "首行缩进(cm)", min: 0, max: 6, step: 0.1 },
  { key: "paragraphSpaceBeforePt", label: "段前(pt)", min: 0, max: 72, step: 0.5 },
  { key: "paragraphSpaceAfterPt", label: "段后(pt)", min: 0, max: 72, step: 0.5 },
];

function createEmptyLayoutSettings() {
  return {
    marginTopCm: "",
    marginRightCm: "",
    marginBottomCm: "",
    marginLeftCm: "",
    paragraphLeftIndentCm: "",
    paragraphRightIndentCm: "",
    firstLineIndentCm: "",
    paragraphSpaceBeforePt: "",
    paragraphSpaceAfterPt: "",
  };
}

export default {
  name: "RecognitionUploader",
  props: {
    pollInterval: {
      type: Number,
      default: 1500,
    },
    uploadApi: {
      type: Function,
      default: uploadExamFiles,
    },
    statusApi: {
      type: Function,
      default: getTaskStatus,
    },
    resultApi: {
      type: Function,
      default: getTaskResult,
    },
    detailsApi: {
      type: Function,
      default: getTaskDetails,
    },
    listTasksApi: {
      type: Function,
      default: listRecognitionTasks,
    },
    historyLimit: {
      type: Number,
      default: 200,
    },
  },
  data() {
    return {
      selectedFiles: [],
      uploading: false,
      errorMessage: "",
      ruleProfileId: "",
      ruleProfiles: [],
      taskIds: [],
      taskStateMap: {},
      pollerMap: {},
      pollInFlightMap: {},
      historyItems: [],
      loadingHistory: false,
      viewingTaskId: null,
      showLayoutModal: false,
      layoutFieldDefs: LAYOUT_FIELD_DEFS,
      layoutSettings: createEmptyLayoutSettings(),
      layoutDraft: createEmptyLayoutSettings(),
    };
  },
  mounted() {
    this.loadRuleProfiles();
    this.refreshTaskHistory();
  },
  beforeDestroy() {
    Object.values(this.pollerMap).forEach((timer) => clearInterval(timer));
    this.pollerMap = {};
    this.pollInFlightMap = {};
  },
  computed: {
    layoutSummaryText() {
      const payload = this.normalizeLayoutPayload(this.layoutSettings, false);
      const count = Object.keys(payload).length;
      return count > 0 ? `已设置 ${count} 项` : "使用原文档排版";
    },
  },
  methods: {
    async fetchAllTaskItems() {
      const pageSize = Math.max(1, Number(this.historyLimit) || 200);
      const allItems = [];
      let offset = 0;
      let pageCount = 0;
      const maxPages = 200;

      while (pageCount < maxPages) {
        const payload = await this.listTasksApi(pageSize, offset);
        const items = Array.isArray(payload && payload.items) ? payload.items : [];
        if (items.length === 0) break;

        allItems.push(...items);
        pageCount += 1;

        if (items.length < pageSize) break;
        offset += items.length;
      }

      return allItems;
    },
    openLayoutModal() {
      this.layoutDraft = { ...this.layoutSettings };
      this.showLayoutModal = true;
    },
    closeLayoutModal() {
      this.showLayoutModal = false;
    },
    resetLayoutDraft() {
      this.layoutDraft = createEmptyLayoutSettings();
    },
    applyLayoutModal() {
      try {
        const normalized = this.normalizeLayoutPayload(this.layoutDraft, true);
        this.layoutSettings = { ...createEmptyLayoutSettings(), ...normalized };
        this.showLayoutModal = false;
      } catch (err) {
        this.errorMessage = err.message || "排版参数校验失败";
      }
    },
    normalizeLayoutPayload(source, strict = true) {
      const payload = {};
      this.layoutFieldDefs.forEach((field) => {
        const raw = source ? source[field.key] : "";
        if (raw === null || raw === undefined || raw === "") {
          return;
        }
        const numeric = Number(raw);
        if (!Number.isFinite(numeric)) {
          if (strict) {
            throw new Error(`${field.label} 必须是数字`);
          }
          return;
        }
        if (numeric < field.min || numeric > field.max) {
          if (strict) {
            throw new Error(`${field.label} 范围应为 ${field.min} - ${field.max}`);
          }
          return;
        }
        payload[field.key] = Number(numeric.toFixed(2));
      });
      return payload;
    },
    buildLayoutAdjustmentsPayload() {
      const payload = this.normalizeLayoutPayload(this.layoutSettings, true);
      return Object.keys(payload).length > 0 ? payload : null;
    },
    async loadRuleProfiles() {
      try {
        this.ruleProfiles = await listRuleProfiles();
      } catch (err) {
        this.errorMessage = err.message || "规则列表加载失败";
      }
    },
    async refreshTaskHistory() {
      this.loadingHistory = true;
      try {
        const items = await this.fetchAllTaskItems();
        this.historyItems = items;
        items.forEach((item) => {
          this.$set(this.taskStateMap, item.taskId, {
            taskId: item.taskId,
            status: item.status,
            progress: item.progress,
            errorMessage: item.errorMessage || "",
            fileName: item.fileName,
          });
          // 仅自动轮询“本次上传”的任务，避免刷新页面后对全部历史 pending 任务持续轮询刷日志。
          const shouldAutoPollCurrentBatch =
            this.taskIds.includes(item.taskId) &&
            (item.status === "pending" || item.status === "processing");
          if (shouldAutoPollCurrentBatch && !this.pollerMap[item.taskId]) {
            this.startPolling(item.taskId, false);
          }
        });
      } catch (err) {
        this.errorMessage = err.message || "提取记录加载失败";
      } finally {
        this.loadingHistory = false;
      }
    },
    onFileChange(event) {
      this.selectedFiles = Array.from((event.target && event.target.files) || []);
    },
    getTaskState(taskId) {
      return this.taskStateMap[taskId] || { status: "pending", progress: 0, errorMessage: "" };
    },
    async submitUpload() {
      if (!this.selectedFiles.length) return;
      this.uploading = true;
      this.errorMessage = "";
      try {
        const layoutAdjustments = this.buildLayoutAdjustmentsPayload();
        const response = await this.uploadApi(this.selectedFiles, this.ruleProfileId || null, layoutAdjustments);
        this.taskIds = response.taskIds || [];
        this.$emit("task-created", response);
        const autoPreviewTaskId = this.taskIds.length > 0 ? this.taskIds[0] : null;
        this.taskIds.forEach((taskId) => {
          this.$set(this.taskStateMap, taskId, { status: "pending", progress: 0, errorMessage: "" });
          this.startPolling(taskId, taskId === autoPreviewTaskId);
        });
        await this.refreshTaskHistory();
      } catch (err) {
        this.errorMessage = err.message || "上传失败";
      } finally {
        this.uploading = false;
      }
    },
    updateHistoryTaskState(taskId, statusData) {
      const index = this.historyItems.findIndex((item) => item.taskId === taskId);
      if (index < 0) return;
      const current = this.historyItems[index];
      this.$set(this.historyItems, index, {
        ...current,
        status: statusData.status,
        progress: statusData.progress,
        errorMessage: statusData.errorMessage || "",
      });
    },
    async emitTaskFinished(taskId) {
      const [result, details] = await Promise.all([
        this.resultApi(taskId),
        this.detailsApi(taskId),
      ]);
      this.$emit("task-finished", { taskId, result, details });
    },
    startPolling(taskId, emitFinished = true) {
      if (this.pollerMap[taskId]) {
        clearInterval(this.pollerMap[taskId]);
      }
      this.$set(this.pollInFlightMap, taskId, false);

      const stopPolling = () => {
        if (this.pollerMap[taskId]) {
          clearInterval(this.pollerMap[taskId]);
        }
        this.$delete(this.pollerMap, taskId);
        this.$delete(this.pollInFlightMap, taskId);
      };

      const run = async () => {
        if (this.pollInFlightMap[taskId]) {
          return;
        }
        this.$set(this.pollInFlightMap, taskId, true);
        try {
          const statusData = await this.statusApi(taskId);
          this.$set(this.taskStateMap, taskId, statusData);
          this.updateHistoryTaskState(taskId, statusData);
          if (statusData.status === "succeeded") {
            stopPolling();
            if (emitFinished) {
              await this.emitTaskFinished(taskId);
            }
          } else if (statusData.status === "failed") {
            stopPolling();
            this.$emit("task-failed", { taskId, errorMessage: statusData.errorMessage || "" });
          }
        } catch (err) {
          stopPolling();
          this.$emit("task-failed", { taskId, errorMessage: err.message || "查询任务失败" });
        } finally {
          if (Object.prototype.hasOwnProperty.call(this.pollInFlightMap, taskId)) {
            this.$set(this.pollInFlightMap, taskId, false);
          }
        }
      };
      this.pollerMap[taskId] = setInterval(run, this.pollInterval);
      run();
    },
    async viewTask(taskId) {
      this.viewingTaskId = taskId;
      this.errorMessage = "";
      try {
        const statusData = await this.statusApi(taskId);
        this.$set(this.taskStateMap, taskId, statusData);
        this.updateHistoryTaskState(taskId, statusData);
        if (statusData.status !== "succeeded") {
          if (statusData.status === "failed") {
            this.errorMessage = statusData.errorMessage || "该任务识别失败，无法查看结果";
            return;
          }
          this.errorMessage = "任务处理中，完成后会自动展示该任务结果";
          this.startPolling(taskId, true);
          return;
        }
        await this.emitTaskFinished(taskId);
      } catch (err) {
        this.errorMessage = err.message || "加载任务结果失败";
      } finally {
        this.viewingTaskId = null;
      }
    },
  },
};
</script>

<style scoped>
.recognition-uploader {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 12px;
  background: #fafafa;
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.row label {
  width: 88px;
  font-weight: 600;
}

.file-input,
.select {
  flex: 1;
}

.btn {
  height: 32px;
  border: 1px solid #409eff;
  background: #409eff;
  color: #fff;
  border-radius: 4px;
  padding: 0 14px;
  cursor: pointer;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.config-btn {
  height: 32px;
  border: 1px solid #409eff;
  background: #fff;
  color: #409eff;
  border-radius: 4px;
  padding: 0 12px;
  cursor: pointer;
}

.hint {
  color: #606266;
  font-size: 12px;
}

.file-list-row {
  align-items: flex-start;
}

.selected-files {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-tag {
  font-size: 12px;
  background: #ecf5ff;
  color: #409eff;
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  padding: 2px 8px;
}

.history-header {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.refresh-btn {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  height: 28px;
  padding: 0 10px;
  background: #fff;
  color: #606266;
  cursor: pointer;
}

.refresh-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.empty {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

.task-list {
  margin-top: 8px;
  max-height: 260px;
  overflow-y: auto;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
}

.task-main {
  min-width: 0;
  flex: 1;
}

.task-file {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  font-size: 13px;
  color: #909399;
}

.task-error {
  margin-top: 2px;
  font-size: 12px;
  color: #f56c6c;
}

.view-btn {
  border: 1px solid #409eff;
  background: #409eff;
  color: #fff;
  border-radius: 4px;
  height: 28px;
  padding: 0 10px;
  cursor: pointer;
  white-space: nowrap;
}

.view-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.error {
  color: #f56c6c;
  font-size: 13px;
}

.layout-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}

.layout-modal {
  width: min(560px, calc(100vw - 32px));
  background: #fff;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.layout-modal-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}

.layout-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.layout-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}

.layout-input {
  height: 30px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 0 8px;
}

.layout-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.modal-btn {
  height: 30px;
  border-radius: 4px;
  padding: 0 12px;
  cursor: pointer;
}

.modal-btn.light {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
}

.modal-btn.primary {
  border: 1px solid #409eff;
  background: #409eff;
  color: #fff;
}

@media (max-width: 640px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
