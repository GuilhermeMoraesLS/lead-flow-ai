ALTER FUNCTION private.receive_test_event(uuid,text,text,text,text,text,text,text,text,timestamptz,text)
  SET plpgsql.variable_conflict = 'use_column';
