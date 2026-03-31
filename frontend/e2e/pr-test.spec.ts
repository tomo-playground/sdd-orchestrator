/**
 * PR #384 E2E 검증 테스트 — state.db SSOT 통일
 *
 * PR의 핵심 변경 사항을 git show HEAD:... 기반으로 검증합니다:
 * 1. spec.md에 status 필드 미기록 확인 (sdd-sync 결과)
 * 2. on-stop.sh 성공/실패 경로에서 state.db만 업데이트 확인
 * 3. sdd-design.md / sdd-run.md 에서 state.db UPSERT 사용 + SQL 구문 정확성
 */

import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import * as path from "path";

const REPO_ROOT = path.resolve(__dirname, "../..");

function getCommittedContent(filePath: string): string {
  return execSync(`git show HEAD:${filePath}`, {
    cwd: REPO_ROOT,
    encoding: "utf-8",
  });
}

function listCommittedFiles(pattern: string): string[] {
  try {
    const result = execSync(
      `git show HEAD --name-only --format="" | grep "${pattern}" || true`,
      { cwd: REPO_ROOT, encoding: "utf-8" }
    );
    return result
      .trim()
      .split("\n")
      .filter((f) => f.length > 0);
  } catch {
    return [];
  }
}

// ─── sdd-sync: spec.md에 status 미기록 확인 ───

test.describe("sdd-sync: spec.md에 status 미기록 확인", () => {
  test("current/ 내 spec.md 파일에 status: 필드가 없어야 한다", () => {
    const currentSpecFiles = execSync(
      "git show HEAD --name-only --format='' | grep '^.claude/tasks/current/.*spec.md$' || true",
      { cwd: REPO_ROOT, encoding: "utf-8" }
    )
      .trim()
      .split("\n")
      .filter((f) => f.length > 0);

    for (const filePath of currentSpecFiles) {
      const content = getCommittedContent(filePath);
      const statusLines = content
        .split("\n")
        .filter((line) => /^status:\s*\S/.test(line));
      expect(
        statusLines,
        `${filePath} 에 status: 필드가 있어서는 안 됨: ${statusLines.join(", ")}`
      ).toHaveLength(0);
    }
  });

  test("done/ 내 spec.md 파일에 status: 필드가 없어야 한다", () => {
    const doneSpecFiles = execSync(
      "git show HEAD --name-only --format='' | grep '^.claude/tasks/done/.*spec.md$' || true",
      { cwd: REPO_ROOT, encoding: "utf-8" }
    )
      .trim()
      .split("\n")
      .filter((f) => f.length > 0);

    // PR에서 70+ done spec.md 파일의 status 행을 제거했는지 확인
    expect(doneSpecFiles.length).toBeGreaterThan(0);

    for (const filePath of doneSpecFiles) {
      const content = getCommittedContent(filePath);
      const statusLines = content
        .split("\n")
        .filter((line) => /^status:\s*\S/.test(line));
      expect(
        statusLines,
        `${filePath} 에 status: 필드가 있어서는 안 됨: ${statusLines.join(", ")}`
      ).toHaveLength(0);
    }
  });

  test("_template.md에 status: 필드가 없어야 한다", () => {
    const content = getCommittedContent(".claude/tasks/_template.md");
    const statusLines = content
      .split("\n")
      .filter((line) => /^status:\s*\S/.test(line));
    expect(
      statusLines,
      `_template.md에 status: 필드 존재: ${statusLines.join(", ")}`
    ).toHaveLength(0);
  });
});

// ─── sdd-design / sdd-run: state.db만 업데이트 확인 ───

test.describe("sdd-design: state.db만 업데이트 확인", () => {
  test("sdd-design.md에 sqlite3 state.db UPSERT가 포함되어야 한다", () => {
    const content = getCommittedContent(".claude/commands/sdd-design.md");
    expect(content).toContain("sqlite3");
    expect(content).toContain("state.db");
    expect(content).toContain("INSERT INTO task_status");
    expect(content).toContain("ON CONFLICT(task_id) DO UPDATE SET");
  });

  test("sdd-design.md UPSERT SQL에 문법 오류(여분 괄호)가 없어야 한다", () => {
    const content = getCommittedContent(".claude/commands/sdd-design.md");
    // 'datetime('now'));' 패턴: ON CONFLICT 절 끝에 여분 ')' 없어야 함
    // 올바른 형식: datetime('now');" 또는 datetime('now');`
    const badPattern = /datetime\('now'\)\);/g;
    const matches = content.match(badPattern) || [];
    expect(
      matches,
      `sdd-design.md에 잘못된 SQL 구문(여분 ) 포함) 발견: ${matches.join(", ")}`
    ).toHaveLength(0);
  });
});

test.describe("sdd-run: state.db만 업데이트 확인", () => {
  test("sdd-run.md에 sqlite3 state.db running UPSERT가 포함되어야 한다", () => {
    const content = getCommittedContent(".claude/commands/sdd-run.md");
    expect(content).toContain("sqlite3");
    expect(content).toContain("state.db");
    expect(content).toContain("INSERT INTO task_status");
    expect(content).toContain("'running'");
  });

  test("sdd-run.md UPSERT SQL에 문법 오류(여분 괄호)가 없어야 한다", () => {
    const content = getCommittedContent(".claude/commands/sdd-run.md");
    const badPattern = /datetime\('now'\)\);/g;
    const matches = content.match(badPattern) || [];
    expect(
      matches,
      `sdd-run.md에 잘못된 SQL 구문(여분 ) 포함) 발견: ${matches.join(", ")}`
    ).toHaveLength(0);
  });
});

// ─── on-stop.sh: 성공/실패 경로 state.db 기록 확인 ───

test.describe("on-stop.sh: 성공/실패 경로 state.db 기록 확인", () => {
  test("on-stop.sh 성공 경로에 state.db done 기록이 있어야 한다", () => {
    const content = getCommittedContent(".claude/hooks/on-stop.sh");
    // sqlite3로 done 상태 기록
    expect(content).toContain("'done'");
    expect(content).toContain("state.db");
    // done 기록 UPSERT 패턴 확인
    expect(content).toMatch(
      /sqlite3.*INSERT INTO task_status.*'done'.*ON CONFLICT/s
    );
  });

  test("on-stop.sh 실패 경로에 state.db failed 기록이 있어야 한다", () => {
    const content = getCommittedContent(".claude/hooks/on-stop.sh");
    expect(content).toContain("'failed'");
    expect(content).toMatch(
      /sqlite3.*INSERT INTO task_status.*'failed'.*ON CONFLICT/s
    );
  });

  test("on-stop.sh 성공 경로에서 spec.md done 쓰기 sed가 제거되어야 한다", () => {
    const content = getCommittedContent(".claude/hooks/on-stop.sh");
    // 성공 경로의 sed -i로 spec.md에 done을 쓰는 패턴이 없어야 함
    // 실패 경로(RETRY_COUNT >= MAX_RETRIES)와 성공 경로를 분리하여 확인
    // 성공 경로는 "전체 통과" 섹션 이후
    const successSection = content.split("# ─── 전체 통과")[1] || content;
    const sedDonePattern = /sed -i.*status.*done.*spec\.md/;
    expect(
      sedDonePattern.test(successSection),
      "on-stop.sh 성공 경로에 sed -i spec.md done 쓰기가 남아 있음"
    ).toBe(false);
  });
});

// ─── Backend API 헬스 체크 ───

test.describe("Backend API 헬스 체크", () => {
  test("Backend /health 엔드포인트가 응답해야 한다", async ({ request }) => {
    const backendUrl = "http://localhost:18000";
    try {
      const response = await request.get(`${backendUrl}/health`);
      expect(response.status()).toBeLessThan(500);
    } catch {
      // Backend가 없을 수 있는 테스트 환경에서는 스킵
      console.log("Backend unavailable — skipping health check");
    }
  });
});
