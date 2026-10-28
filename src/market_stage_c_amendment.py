"""Original frozen I4 fixture guarded by the accepted no-fit diagnostic rule."""
from panel_diagnostic import compare_panels,panel_hash


class FixtureGuardError(ValueError):
    def __init__(self,message,receipt):
        super().__init__(message)
        self.receipt=receipt


def original_fixture(original,regenerated,expected_hash):
    """Return the original object unchanged, never the regenerated fixture."""
    actual=panel_hash(original)
    if actual!=expected_hash:
        receipt=dict(status='blocked',reason='original_fixture_hash',expected_original_sha256=expected_hash,
                     actual_original_sha256=actual)
        raise FixtureGuardError('Original I4 fixture hash differs',receipt)
    comparison=compare_panels(original,regenerated,relative_tolerance=1e-9)
    receipt=dict(status='accepted' if comparison['classification']=='A' else 'blocked',
        original_fixture_sha256=actual,regenerated_sha256=panel_hash(regenerated),comparison=comparison,
        scope='Fixture admissibility only; no scoring tolerance; original object retained verbatim')
    if comparison['classification']!='A':
        raise FixtureGuardError('Regenerated I4 panels are not class A',receipt)
    return original,receipt
