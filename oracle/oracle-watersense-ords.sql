
-- ORDS configuration to expose services from the database.

-- Drop existing RESTful services for the WATERSENSE schema if they exist
-- This is necessary to ensure a clean setup without conflicts
-- Ensure you are logged in as the administrator to run this setup
-- Set the current schema to WATERSENSE to ensure all subsequent operations
--(such as enabling ORDS and defining modules/services) are executed in the correct schema context.
alter session set current_schema = watersense;

BEGIN
  ORDS.DROP_REST_FOR_SCHEMA(
    p_schema => 'WATERSENSE'
  );
  COMMIT;
END;
/

-- Enable the schema for RESTful services

BEGIN
-- Single base path for WATERSENSE schema
  ORDS.ENABLE_SCHEMA(
    p_enabled            => TRUE,
    p_schema             => 'WATERSENSE',
    p_url_mapping_type   => 'BASE_PATH',
    p_url_mapping_pattern => 'watersense',
    p_auto_rest_auth     => FALSE   -- By setting this to FALSE, all endpoints in this schema are open (do not require authentication) by default; authentication must be explicitly enabled per endpoint if needed, so review security requirements carefully.
  );
  COMMIT;
END;
/

-- Define RESTful services for the WATERSENSE schema
BEGIN
  -- Public API (open access)
    ORDS.DEFINE_MODULE(
    p_module_name => 'public_api',
    p_base_path   => 'public',
    p_items_per_page => 0
  );

  -- (appuser) User registration API (Open access)
    ORDS.DEFINE_MODULE(
    p_module_name => 'appuser_api',
    p_base_path   => 'appuser',
    p_items_per_page => 0
  );

  -- Admin API (auth required)
    ORDS.DEFINE_MODULE(
    p_module_name => 'admin_api',
    p_base_path   => 'admin',
    p_items_per_page => 0
  );

  COMMIT;
END;
/

-- Retrieve public/river information
BEGIN
  ORDS.DEFINE_SERVICE(
    p_module_name    => 'public_api',
    p_base_path      => 'public',
    p_pattern        => 'river',
    p_method         => 'GET',
    p_source_type    => ORDS.source_type_query,
    p_source         => '
      SELECT *
      FROM river
      WHERE (:name IS NULL OR LOWER(rivername) LIKE ''%'' || LOWER(:name) || ''%'')
      AND (:id IS NULL OR riverid = :id)
    '
  );
  COMMIT;
END;
/

-- Register a new user via the API
BEGIN

  ORDS.DEFINE_SERVICE(
    p_module_name    => 'appuser_api',
    p_base_path      => 'appuser',
    p_pattern        => 'register',
    p_method         => 'POST',
    p_source_type    => ORDS.source_type_plsql,
    p_source         => '
        BEGIN
          register_user(
              p_displayname => :displayname,
              p_email       => :email,
              p_password    => :password
          );
        END;'
  );

  COMMIT;
END;
/

