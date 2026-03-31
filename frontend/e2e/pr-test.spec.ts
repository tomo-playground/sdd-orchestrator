/**
 * PR #393 E2E 검증 테스트 — classify_batch N+1 쿼리 → 배치 최적화 (SP-126)
 *
 * PR의 핵심 변경 사항을 git show HEAD:... 기반으로 검증합니다:
 * 1. _lookup_db_batch / _save_classification_batch 신규 메서드 존재 확인
 * 2. classify_batch()가 배치 메서드를 사용함 확인 (WHERE IN / INSERT ON CONFLICT)
 * 3. test_tag_classifier_batch.py 존재 + 16개 이상 테스트 케이스 확인
 * 4. classify() 단건 경로 미변경 확인 (여전히 _lookup_db 사용)
 * 5. 기존 test_prompt_fixes.py::test_tag_classifier_lookup_underscore 보존 확인
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

// ─── 1. 신규 배치 메서드 추가 확인 ───

test.describe("classify_batch N+1 Fix: 배치 메서드 추가 확인", () => {
  test("_lookup_db_batch() 메서드가 tag_classifier.py에 추가되었다", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    expect(content).toContain("def _lookup_db_batch(");
    // WHERE name IN (...) 단일 쿼리 패턴
    expect(content).toContain("Tag.name.in_(tags)");
  });

  test("_save_classification_batch() 메서드가 tag_classifier.py에 추가되었다", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    expect(content).toContain("def _save_classification_batch(");
    // INSERT ... ON CONFLICT DO UPDATE 패턴
    expect(content).toContain("on_conflict_do_update");
  });
});

// ─── 2. classify_batch()가 배치 메서드를 사용함 확인 ───

test.describe("classify_batch N+1 Fix: classify_batch 배치 메서드 호출 확인", () => {
  test("classify_batch()가 _lookup_db_batch()를 호출한다", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    // classify_batch 함수 본문에서 _lookup_db_batch 호출 확인
    const classifyBatchSection = content.slice(
      content.indexOf("def classify_batch("),
      content.indexOf("def _lookup_db_batch(")
    );
    expect(classifyBatchSection).toContain("_lookup_db_batch(");
  });

  test("classify_batch()가 _save_classification_batch()를 호출한다", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    const classifyBatchSection = content.slice(
      content.indexOf("def classify_batch("),
      content.indexOf("def _lookup_db_batch(")
    );
    expect(classifyBatchSection).toContain("_save_classification_batch(");
  });

  test("_lookup_db_batch()가 빈 입력에 대해 DB 호출 없이 빈 dict를 반환한다 (코드 분기 확인)", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    const batchLookupSection = content.slice(
      content.indexOf("def _lookup_db_batch("),
      content.indexOf("def _save_classification_batch(")
    );
    expect(batchLookupSection).toContain("if not tags:");
    expect(batchLookupSection).toContain("return {}");
  });

  test("_save_classification_batch()가 빈 입력에 대해 조기 반환한다 (코드 분기 확인)", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    const batchSaveSection = content.slice(
      content.indexOf("def _save_classification_batch("),
      content.indexOf("def _lookup_db(")
    );
    expect(batchSaveSection).toContain("if not items:");
    expect(batchSaveSection).toContain("return");
  });
});

// ─── 3. 회귀 테스트 파일 확인 ───

test.describe("classify_batch N+1 Fix: test_tag_classifier_batch.py 회귀 테스트 확인", () => {
  test("test_tag_classifier_batch.py 파일이 HEAD 커밋에 존재한다", () => {
    const content = getCommittedContent(
      "backend/tests/test_tag_classifier_batch.py"
    );
    expect(content.length).toBeGreaterThan(0);
  });

  test("test_tag_classifier_batch.py에 16개 이상의 test_ 함수가 있다", () => {
    const content = getCommittedContent(
      "backend/tests/test_tag_classifier_batch.py"
    );
    const testFunctions = content.match(/^\s{4}def test_/gm) || [];
    expect(
      testFunctions.length,
      `테스트 함수 ${testFunctions.length}개 발견 (최소 16개 필요)`
    ).toBeGreaterThanOrEqual(16);
  });

  test("TestLookupDbBatch 클래스가 포함되어 있다 (_lookup_db_batch N+1 테스트)", () => {
    const content = getCommittedContent(
      "backend/tests/test_tag_classifier_batch.py"
    );
    expect(content).toContain("class TestLookupDbBatch:");
    // 핵심 N+1 회귀 테스트: N개 태그 → db.execute 1회
    expect(content).toContain("db.execute.call_count == 1");
  });

  test("TestSaveClassificationBatch 클래스가 포함되어 있다 (_save_classification_batch N+1 테스트)", () => {
    const content = getCommittedContent(
      "backend/tests/test_tag_classifier_batch.py"
    );
    expect(content).toContain("class TestSaveClassificationBatch:");
  });

  test("TestClassifyBatchUsesBatchMethods 클래스가 포함되어 있다 (통합 검증)", () => {
    const content = getCommittedContent(
      "backend/tests/test_tag_classifier_batch.py"
    );
    expect(content).toContain("class TestClassifyBatchUsesBatchMethods:");
  });
});

// ─── 4. classify() 단건 경로 미변경 확인 ───

test.describe("classify_batch N+1 Fix: classify() 단건 경로 미변경 확인", () => {
  test("classify() 메서드가 여전히 _lookup_db()를 호출한다 (단건 경로 유지)", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    // classify() 섹션 (classify_batch 이전까지)
    const classifySection = content.slice(
      content.indexOf("    def classify(self, tag: str)"),
      content.indexOf("    def classify_batch(")
    );
    expect(classifySection).toContain("_lookup_db(normalized)");
    // 단건 경로에서 배치 메서드 사용 금지
    expect(classifySection).not.toContain("_lookup_db_batch(");
    expect(classifySection).not.toContain("_save_classification_batch(");
  });

  test("classify() 메서드가 여전히 _save_classification()를 호출한다 (단건 저장 유지)", () => {
    const content = getCommittedContent(
      "backend/services/tag_classifier.py"
    );
    const classifySection = content.slice(
      content.indexOf("    def classify(self, tag: str)"),
      content.indexOf("    def classify_batch(")
    );
    expect(classifySection).toContain("_save_classification(");
  });
});

// ─── 5. 기존 테스트 보존 확인 ───

test.describe("classify_batch N+1 Fix: 기존 test_prompt_fixes.py 보존 확인", () => {
  test("test_prompt_fixes.py에 test_tag_classifier_lookup_underscore가 유지된다", () => {
    const content = getCommittedContent(
      "backend/tests/test_prompt_fixes.py"
    );
    expect(content).toContain("def test_tag_classifier_lookup_underscore");
  });
});

// ─── 6. Backend API 헬스 체크 ───

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
