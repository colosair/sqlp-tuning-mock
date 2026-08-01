<!--meta
번호: 4
대상장: 2
대상절: 2.3
절제목: 응답 시간 분석
문제유형: 적절한_것
보조자료: 없음
DBMS: 오라클
정답: 2
선택지유형: 서술형
함정유형: [같은것_다른이름]
대상개념: [Response_Time_Analysis, AWR, Wait_Time]
자극물밀도: 없음
계산요구: 없음
출처: 생성
상태: 검수완료
-->

## 문제 4

### 문제

AWR/ASH 보고서로 응답 시간을 분석할 때의 `응답 시간 = CPU + Wait` 구조와 DB Time, Top 대기 이벤트 해석에 대한 설명으로 가장 적절한 것은?

### 선택지

① 응답 시간은 Service Time과 CPU Time, 그리고 Wait Time을 각각 따로 집계해 더한 값이므로, AWR의 Top Timed Events에서 `DB CPU` 행과 서비스 시간 항목을 별개의 두 항으로 놓고 대기 이벤트 시간까지 세 항을 합산해야 정확한 응답 시간이 나온다.

② 응답 시간은 CPU를 실제로 소비한 Service Time과 자원을 확보하려 기다린 Wait Time으로 나뉘며, AWR의 Top Timed Events에서 상위 이벤트가 DB Time에서 차지하는 비중을 보면 병목이 CPU 쪽인지 특정 대기 쪽인지 가늠할 수 있다.

③ AWR 보고서의 DB Time은 두 스냅샷 사이의 실제 경과 시간(wall-clock elapsed)과 같은 값이므로, DB Time이 경과 시간의 몇 배로 찍혔다면 스냅샷 구간이 잘못 잡혔다는 뜻이고, Top Timed Events의 비중도 DB Time이 아니라 경과 시간으로 나눠 읽어야 한다.

④ 대기 이벤트 목록에서 `db file sequential read`처럼 이름에 대기가 드러난 이벤트의 시간만 Wait Time이자 응답 시간이고, CPU를 쓴 시간은 일한 시간이라 응답 시간에서 빼야 하므로, Top Timed Events의 `DB CPU` 행은 병목 판단에서 제외하는 것이 옳다.

---

### 정답 — ②

### 왜 ②인가

응답 시간 분석의 뼈대는 시간을 **두 조각**으로 가르는 것입니다.

```text
응답 시간(Response Time) = Service Time + Wait Time
   Service Time : CPU를 실제로 쓴 시간   ← 'CPU Time'이 곧 Service Time (같은 것)
   Wait Time    : 자원(블록·락·로그 등)을 기다린 시간

DB Time = 모든 세션의 (CPU 소비 + 대기)를 합산한 값
   → 세션이 여러 개면 wall-clock 경과 시간을 훨씬 넘어설 수 있다 (같지 않음)

Top Timed Events : 상위 이벤트가 DB Time에서 차지하는 '비중'으로 병목의 성격을 판별
```

②는 이 구조를 정확히 짚었습니다. 응답 시간을 Service(=CPU) Time과 Wait Time으로 나누고, Top Timed Events의 비중으로 병목이 CPU 쪽인지 특정 대기 쪽인지 읽는 것이 AWR/ASH 해석의 정석입니다.

①·③·④는 각각 개념의 경계를 흐린 함정입니다.

- ①은 **Service Time과 CPU Time을 서로 다른 항인 양** 따로 더하게 했습니다. 둘은 같은 것(서비스 시간 = CPU 소비 시간)이므로 이렇게 더하면 CPU 시간을 이중 계산합니다.
- ③은 DB Time을 wall-clock 경과 시간과 같다고 했지만, DB Time은 세션들의 시간을 합산한 값이라 경과 시간을 넘어설 수 있습니다. 몇 배로 찍히는 것은 스냅샷 구간 오류가 아니라 동시 세션이 많았다는 정상 신호이고, 비중도 DB Time으로 나눠 읽습니다.
- ④는 CPU를 쓴 시간(Service Time)을 응답 시간에서 빼 버렸습니다. CPU 시간도 응답 시간의 한 축이라 `DB CPU` 행이야말로 CPU 바운드인지 가르는 근거입니다.

### 오답 이유

| 선택지 | 판정 | 이유 |
|:-:|:-:|---|
| ① | ✗ | Service Time과 CPU Time은 같은 것(서비스 시간 = CPU 소비 시간)입니다. Top Timed Events의 `DB CPU`가 곧 그 서비스 시간이므로, 다른 이름을 별개 항으로 놓고 세 항을 더하면 CPU 시간을 이중 계산하게 됩니다 |
| ② | **○** | 응답 시간을 Service(=CPU) Time과 Wait Time으로 가르고, Top Timed Events의 DB Time 비중으로 병목의 성격을 판별하는 것이 AWR 해석의 정석입니다 |
| ③ | ✗ | DB Time은 모든 세션의 CPU+대기를 합산한 값이라 두 스냅샷 사이 경과 시간을 넘어설 수 있습니다. 경과 시간의 몇 배로 찍히는 것은 스냅샷 오류가 아니라 동시 세션이 많았다는 신호이고, 이벤트 비중도 경과 시간이 아니라 DB Time으로 나눠 읽습니다 |
| ④ | ✗ | CPU를 쓴 Service Time도 응답 시간의 한 축입니다. 이름에 대기가 든 이벤트만 응답 시간에 넣으면 CPU 시간이 통째로 빠지고, `DB CPU` 행을 병목 판단에서 빼면 CPU 바운드 상황을 아예 못 잡습니다 |

---

## ✅ 이 문제의 핵심

1. **응답 시간 = Service Time + Wait Time.** Service Time은 곧 **CPU Time**이므로 둘을 별개 항으로 나눠 더하면 이중 계산입니다.
2. **DB Time은 세션별 CPU+대기의 합산값**이라, 세션이 여러 개면 wall-clock 경과 시간을 넘어설 수 있습니다.
3. **Top Timed Events의 DB Time 비중**으로 병목이 CPU 쪽인지 특정 대기 쪽인지 가늠합니다.
4. CPU를 쓴 시간도 응답 시간의 한 축이므로, 대기 이벤트만 응답 시간으로 보면 안 됩니다.

📌 한 줄 정리: 응답 시간은 Service(=CPU) Time과 Wait Time의 합이고 Top Timed Events의 DB Time 비중으로 병목을 읽으며, Service Time을 CPU Time과 별개 항으로 더하는 것은 같은 것을 다른 이름으로 이중 계산하는 오류입니다.
