
-- ORDS configuration to expose services from the database.

BEGIN
  ORDS.ENABLE_SCHEMA(
    p_enabled      => TRUE,
    p_schema       => 'WATERSENSE',
    p_url_mapping_type => 'BASE_PATH',
    p_url_mapping_pattern  => 'appuser',
    p_auto_rest_auth => FALSE
  );
  COMMIT;
END;
/

BEGIN
  ORDS.DEFINE_SERVICE(
    p_module_name    => 'appuser_api',
    p_base_path      => '/appuser/',
    p_pattern        => 'register/',
    p_method         => 'POST',
    p_source_type    => ORDS.source_type_plsql,
    p_source         => '
      BEGIN
        register_user(
          p_displayname => :displayname,
          p_email       => :email,
          p_password    => :password
        );
      END;',
    p_items_per_page => 0
  );

  COMMIT;
END;
/
