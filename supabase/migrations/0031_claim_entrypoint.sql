-- The prior claim function lacks SL-07 cancellation/pending semantics.
REVOKE EXECUTE ON FUNCTION private.claim_conversation(uuid,uuid,integer) FROM app_api;
