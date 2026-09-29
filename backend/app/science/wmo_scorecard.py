"""Retrospective categorical scorecard; unavailable lead pairs remain unscored."""

from backend.app.schemas.scorecard import ScorecardLead, WmoScorecard
from backend.app.schemas.verification import VerificationReport
from backend.app.science.verification import ContingencyTable, categorical_scores


LEADS = (15, 30, 45, 60, 90, 120)


def build_wmo_scorecard(report: VerificationReport) -> WmoScorecard:
    by_lead = {lead.lead_minutes: lead for lead in report.leads}
    rows: list[ScorecardLead] = []
    for lead_minutes in LEADS:
        lead = by_lead.get(lead_minutes)
        if lead is None:
            reason = (
                "Forecast horizon ends at T+60; no paired forecast and observation."
                if lead_minutes > 60 else
                "No observed replay frame paired with this forecast lead."
            )
            rows.append(ScorecardLead(lead_minutes=lead_minutes, status="NOT_COMPUTABLE", reason=reason))
            continue
        scores = categorical_scores(ContingencyTable(
            hits=lead.hits, misses=lead.misses,
            false_alarms=lead.false_alarms, correct_negatives=lead.correct_negatives,
        ))
        rows.append(ScorecardLead(
            lead_minutes=lead_minutes, status="COMPUTED",
            hits=lead.hits, misses=lead.misses, false_alarms=lead.false_alarms,
            correct_negatives=lead.correct_negatives, pod=scores.pod, far=scores.far,
            csi=scores.csi, hss=scores.heidke_skill_score,
            reason="No event denominator; metric undefined." if None in (scores.pod, scores.far, scores.csi, scores.heidke_skill_score) else None,
        ))
    return WmoScorecard(
        event_id=report.event_id, source=report.source, evidence_status=report.evidence_status,
        method=report.method, field=report.field, threshold=report.threshold,
        threshold_unit=report.threshold_unit, georeferenced=report.georeferenced,
        observation_source=report.observation_source, leads=rows,
        limitations=report.limitations,
    )
