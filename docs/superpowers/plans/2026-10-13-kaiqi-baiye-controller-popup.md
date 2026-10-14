# 开启百业与控制器弹窗 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 返回百业支持「开启百业」；公共控制器弹窗（取消优先/确认）供各界面任务 JumpBack 关闭。

**Architecture:** `public_task.json` 新增公共节点；`return_baiye_task.json` 加引导页；买药改挂公共；各任务 on_error 前置 `[JumpBack]公共_关控制器弹窗`。

**Tech Stack:** MaaFramework pipeline JSON, OCR, JumpBack

## Global Constraints

- JumpBack 回失败节点，不回入口
- 控制器：取消优先，再确认
- 退出游戏本轮不挂
- 坐标 1280×720

---

## Task 1: 公共控制器节点

- [ ] `public_task.json` 增加 `公共_关控制器弹窗` / `公共_控制器点取消` / `公共_控制器点确认`
- [ ] `处理异常` next 首项 `[JumpBack]公共_关控制器弹窗`

## Task 2: 返回百业开启百业

- [ ] `回百业_已见开启百业` / `回百业_点开启百业`
- [ ] 入口与点百业接线
- [ ] 文档 `返回百业.md`

## Task 3: 买药迁移 + 其它任务 JumpBack

- [ ] 买药关控制器改挂公共（保留节点名转发或替换引用）
- [ ] 各界面任务 `on_error` 含结束失败处前置 JumpBack
- [ ] 任务流程 / 自动买药文档
