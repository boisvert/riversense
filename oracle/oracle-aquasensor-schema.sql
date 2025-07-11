
/****** Database riversense ******/


/****** Table AppUser ******/

CREATE TABLE AppUser (
    UserID        VARCHAR2(50 CHAR) NOT NULL,
    DisplayName   VARCHAR2(50 CHAR) NOT NULL,
	UserEmail     VARCHAR2(50 CHAR) NOT NULL UNIQUE,
    PasswordHash  VARCHAR2(64 CHAR) NOT NULL, -- 32-byte SHA256 hash in hex (64 characters)
    Salt          VARCHAR2(32 CHAR) NOT NULL, -- 16 random bytes in hex (32 characters)
    UserRole      VARCHAR2(10) DEFAULT 'pending' CHECK (UserRole IN ('admin', 'editor', 'viewer', 'pending')),
    UserStatus    VARCHAR2(8) DEFAULT 'inactive' CHECK (UserStatus IN ('active', 'inactive')),
    CreatedAt     TIMESTAMP DEFAULT SYSTIMESTAMP,
    PasswordResetToken   VARCHAR2(64 CHAR),
    PasswordResetExpiry  TIMESTAMP,
    CONSTRAINT PK_AppUser PRIMARY KEY (UserID),
	CONSTRAINT chk_email_format CHECK (REGEXP_LIKE(UserEmail, '^[^@]+@[^@]+\.[^@]+$')),
	CONSTRAINT chk_hash CHECK (REGEXP_LIKE(PasswordHash,'^[A-F0-9]{64}$'))
);

CREATE SEQUENCE seq_appuser_id START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE FUNCTION generate_appuser_id RETURN VARCHAR2 IS
BEGIN
    RETURN 'user' || TO_CHAR(seq_appuser_id.NEXTVAL);
END;
/

CREATE OR REPLACE FUNCTION generate_salt RETURN VARCHAR2 IS
    v_raw RAW(16);
BEGIN
    v_raw := DBMS_CRYPTO.RANDOMBYTES(16);
    RETURN RAWTOHEX(v_raw);
END;
/

CREATE OR REPLACE FUNCTION hash_password(p_password VARCHAR2, p_salt VARCHAR2) RETURN VARCHAR2 IS
    v_hash RAW(32);
BEGIN
    v_hash := DBMS_CRYPTO.HASH(
        UTL_I18N.STRING_TO_RAW(p_password || p_salt, 'AL32UTF8'),
        DBMS_CRYPTO.HASH_SH256
    );
    RETURN RAWTOHEX(v_hash);
END;
/

CREATE OR REPLACE PROCEDURE register_user (
    p_displayname   IN VARCHAR2,
    p_email         IN VARCHAR2,
    p_password      IN VARCHAR2
) AS
    v_userid  VARCHAR2(50);
    v_salt    VARCHAR2(32);
    v_hash    VARCHAR2(64);
	v_dummy   NUMBER;

BEGIN
    -- Check for existing user
	
	BEGIN
        SELECT 1 INTO v_dummy
        FROM appuser
        WHERE LOWER(displayname) = LOWER(p_displayname)
           OR LOWER(useremail) = LOWER(p_email);

        -- If found, raise error
        RAISE_APPLICATION_ERROR(-20001, 'Name or email already exists.');
    EXCEPTION
        WHEN NO_DATA_FOUND THEN NULL; -- ok, proceed
	END;

    -- normalise input	
	v_userid := generate_appuser_id();
    v_salt   := generate_salt();
    v_hash   := hash_password(p_password, v_salt);

    -- Insert new user
    INSERT INTO AppUser (
        UserID, DisplayName, UserEmail, PasswordHash, Salt
    ) VALUES (
        v_userid, LOWER(p_displayname), LOWER(p_email), v_hash, v_salt
    );
END;
/

CREATE OR REPLACE FUNCTION verify_app_user (
    p_email IN VARCHAR2,
    p_password IN VARCHAR2
) RETURN VARCHAR2 IS
    v_salt appuser.salt%TYPE;
    v_hash appuser.passwordhash%TYPE;
    v_userid appuser.userid%TYPE;
BEGIN
    SELECT salt, passwordhash, userid
    INTO v_salt, v_hash, v_userid
    FROM appuser
    WHERE LOWER(useremail) = LOWER(p_email)
      AND userstatus = 'active';

    IF hash_password(p_password, v_salt) = v_hash THEN
        RETURN v_userid; -- return user ID on success
    ELSE
        RETURN NULL;
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN NULL;
END;
/

/****** Table River ******/

CREATE TABLE River (
    RiverID      VARCHAR2(50 CHAR) NOT NULL,
    RiverName    VARCHAR2(50 CHAR),
    SourceLat    BINARY_DOUBLE,
    SourceLong   BINARY_DOUBLE,
    MouthLat     BINARY_DOUBLE,
    MouthLong    BINARY_DOUBLE,
	DownRiverID  VARCHAR2(100 CHAR), -- ID of the river this flows in
	ConfBank     CHAR(1) CHECK (ConfBank IN ('L', 'R')), -- flows in left or right bank
    Description  VARCHAR2(400 CHAR),
    Notes        VARCHAR2(3000 CHAR),
	EnteredBy    VARCHAR2(50 CHAR),
    CONSTRAINT PK_River PRIMARY KEY (RiverID),
	CONSTRAINT FK_DownRiver FOREIGN KEY (DownRiverID)
        REFERENCES River (RiverID) ON DELETE SET NULL,
	CONSTRAINT FK_River_EnteredBy FOREIGN KEY (EnteredBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- River: generate IDs
CREATE SEQUENCE seq_river_id START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER trg_river_id_string
BEFORE INSERT ON River
FOR EACH ROW
BEGIN
    IF :NEW.RiverID IS NULL THEN
        SELECT 'river' || TO_CHAR(seq_river_id.NEXTVAL)
        INTO :NEW.RiverID
        FROM dual;
    END IF;
END;
/

/****** Table Place ******/

CREATE TABLE Place (
    PlaceID     VARCHAR2(50 CHAR) NOT NULL,
    RiverID     VARCHAR2(50 CHAR),
    DownRiverPlaceID VARCHAR2(50 CHAR),
    DownRiverRiverID VARCHAR2(50 CHAR),
    DownRiverDistance NUMBER,
    Lat         BINARY_DOUBLE,
    Longitude   BINARY_DOUBLE,
    NearLat     BINARY_DOUBLE,
    NearLong    BINARY_DOUBLE,
    DateChecked TIMESTAMP DEFAULT SYSTIMESTAMP,
    Description VARCHAR2(400 CHAR),
    Notes       VARCHAR2(3000 CHAR),
	EnteredBy   VARCHAR2(50 CHAR),
    CheckedBy   VARCHAR2(50 CHAR),
    CONSTRAINT PK_Place PRIMARY KEY (PlaceID, RiverID),
    CONSTRAINT FK_Place_River FOREIGN KEY (RiverID)
        REFERENCES River (RiverID) ON DELETE SET NULL,
    CONSTRAINT FK_Place_Down_River FOREIGN KEY (DownRiverPlaceID, DownRiverRiverID)
        REFERENCES Place (PlaceID, RiverID) ON DELETE SET NULL,
	CONSTRAINT FK_Place_EnteredBy FOREIGN KEY (EnteredBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL,
	CONSTRAINT FK_Place_CheckedBy FOREIGN KEY (CheckedBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

CREATE SEQUENCE seq_place_id START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER trg_place_id_string
BEFORE INSERT ON Place
FOR EACH ROW
BEGIN
    IF :NEW.PlaceID IS NULL THEN
        SELECT 'place' || TO_CHAR(seq_place_id.NEXTVAL)
        INTO :NEW.PlaceID
        FROM dual;
    END IF;
END;
/

/****** Table PlaceCheck ******/

CREATE TABLE PlaceCheck (
    PlaceID     VARCHAR2(50 CHAR) NOT NULL,
    RiverID     VARCHAR2(50 CHAR) NOT NULL,
    DateChecked TIMESTAMP NOT NULL,
    Description VARCHAR2(400 CHAR),
    Notes       VARCHAR2(3000 CHAR),
	CheckedBy   VARCHAR2(50 CHAR),
    CONSTRAINT PK_PlaceCheck PRIMARY KEY (PlaceID, RiverID, DateChecked),
    CONSTRAINT FK_PlaceCheck_Place FOREIGN KEY (PlaceID, RiverID)
        REFERENCES Place (PlaceID, RiverID) ON DELETE CASCADE,
	CONSTRAINT FK_PlaceCheck_CheckedBy FOREIGN KEY (CheckedBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- Archive past place checks
CREATE OR REPLACE TRIGGER trg_place_check_archive
AFTER UPDATE ON Place
FOR EACH ROW
BEGIN
	IF (
		NVL(:OLD.Description, '¤') != NVL(:NEW.Description, '¤') OR
		NVL(:OLD.Notes, '¤') != NVL(:NEW.Notes, '¤')
	) THEN
    INSERT INTO PlaceCheck (
        PlaceID,
        RiverID,
        DateChecked,
        Description,
        Notes,
        CheckedBy
    ) VALUES (
        :OLD.PlaceID,
        :OLD.RiverID,
        :OLD.DateChecked,
        :OLD.Description,
        :OLD.Notes,
        :OLD.CheckedBy
    );
	END IF;
END;
/

/****** Table Sensor ******/

CREATE TABLE Sensor (
    SensorID      VARCHAR2(50 CHAR) NOT NULL,
    DateChecked   TIMESTAMP DEFAULT SYSTIMESTAMP,
    Status        VARCHAR2(400 CHAR),
    CurrentPlace  VARCHAR2(50 CHAR),
    RiverID       VARCHAR2(50 CHAR),
    DateMoved     TIMESTAMP,
    BatteryLevel  NUMBER(3),
    Notes         VARCHAR2(3000 CHAR),
	EnteredBy     VARCHAR2(50 CHAR),
	UpdatedBy     VARCHAR2(50 CHAR),
	Active        CHAR(1) NOT NULL CHECK (Active IN ('Y', 'N')),
    CONSTRAINT PK_Sensor PRIMARY KEY (SensorID),
    CONSTRAINT FK_Sensor_Place FOREIGN KEY (CurrentPlace, RiverID)
        REFERENCES Place (PlaceID, RiverID) ON DELETE CASCADE,
	CONSTRAINT FK_Sensor_EnteredBy FOREIGN KEY (EnteredBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL,
	CONSTRAINT FK_Sensor_UpdatedBy FOREIGN KEY (UpdatedBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- Sensor: generate IDs, dateMoved default
CREATE SEQUENCE seq_sensor_id START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER trg_sensor_id_string
BEFORE INSERT ON Sensor
FOR EACH ROW
BEGIN
    IF :NEW.SensorID IS NULL THEN
        SELECT 'sensor' || TO_CHAR(seq_sensor_id.NEXTVAL)
        INTO :NEW.SensorID
        FROM dual;
    END IF;
    IF :NEW.DateMoved IS NULL AND
       :NEW.CurrentPlace IS NOT NULL AND
	   :NEW.RiverID IS NOT NULL THEN
        SELECT SYSTIMESTAMP
        INTO :NEW.DateMoved
        FROM dual;
    END IF;
END;
/

/****** Table SensorCheck ******/

CREATE TABLE SensorCheck (
    SensorID      VARCHAR2(50 CHAR) NOT NULL,
    DateChecked   TIMESTAMP NOT NULL,
    Status        VARCHAR2(400 CHAR),
    BatteryLevel  NUMBER(3),  -- match Sensor table
    Notes         VARCHAR2(3000 CHAR),
	CheckedBy     VARCHAR2(50 CHAR),
	Active        CHAR(1) NOT NULL CHECK (Active IN ('Y', 'N')),
    CONSTRAINT PK_SensorCheck PRIMARY KEY (SensorID, DateChecked),
    CONSTRAINT FK_SensorCheck_Sensor FOREIGN KEY (SensorID)
        REFERENCES Sensor (SensorID) ON DELETE CASCADE,
	CONSTRAINT FK_SensorCheck_CheckedBy FOREIGN KEY (CheckedBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- Archive sensor checks
CREATE OR REPLACE TRIGGER trg_sensor_update_archive
AFTER UPDATE ON Sensor
FOR EACH ROW
BEGIN
IF (
    NVL(:OLD.Status, '¤') != NVL(:NEW.Status, '¤') OR
    NVL(:OLD.BatteryLevel, -1) != NVL(:NEW.BatteryLevel, -1) OR
    NVL(:OLD.Notes, '¤') != NVL(:NEW.Notes, '¤')
) THEN
    INSERT INTO SensorCheck (
        SensorID,
        DateChecked,
        Status,
        BatteryLevel,
        Notes,
        CheckedBy,
        Active
    ) VALUES (
        :OLD.SensorID,
        :OLD.DateChecked,
        :OLD.Status,
        :OLD.BatteryLevel,
        :OLD.Notes,
        :OLD.UpdatedBy,
        :OLD.Active
    );
	end if;
END;
/

/****** Table SensorPlace ******/

CREATE TABLE SensorPlace (
    SensorID   VARCHAR2(50 CHAR) NOT NULL,
    PlaceID    VARCHAR2(50 CHAR) NOT NULL,
    RiverID    VARCHAR2(50 CHAR) NOT NULL,
    DateFrom   TIMESTAMP NOT NULL,
    DateTo     TIMESTAMP,
    Notes      VARCHAR2(3000 CHAR),
	MovedBy    VARCHAR2(50 CHAR),
    CONSTRAINT PK_SensorPlace PRIMARY KEY (SensorID, PlaceID, RiverID, DateFrom),
    CONSTRAINT FK_SensorPlace_Place FOREIGN KEY (PlaceID, RiverID)
        REFERENCES Place (PlaceID, RiverID) ON DELETE CASCADE,
    CONSTRAINT FK_SensorPlace_Sensor FOREIGN KEY (SensorID)
        REFERENCES Sensor (SensorID) ON DELETE CASCADE,
	CONSTRAINT FK_MovedBy FOREIGN KEY (MovedBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- archive former sensor's place when a sensor is moved
CREATE OR REPLACE TRIGGER trg_sensor_place_archive
AFTER UPDATE ON Sensor
FOR EACH ROW
BEGIN
IF (
    NVL(:OLD.CurrentPlace, '¤') != NVL(:NEW.CurrentPlace, '¤') OR
    NVL(:OLD.DateMoved, TO_DATE('1900-01-01', 'YYYY-MM-DD')) != NVL(:NEW.DateMoved, TO_DATE('1900-01-01', 'YYYY-MM-DD'))
) THEN
    IF :OLD.CurrentPlace IS NOT NULL AND :OLD.DateMoved IS NOT NULL THEN
        INSERT INTO SensorPlace (
            SensorID,
            PlaceID,
            RiverID,
            DateFrom,
            DateTo,
            Notes,
            MovedBy
        )
        VALUES (
            :OLD.SensorID,
            :OLD.CurrentPlace,
            :OLD.RiverID,
            :OLD.DateMoved,
            SYSTIMESTAMP,
            :OLD.Notes,
            :OLD.UpdatedBy
        );
    END IF;
	end if;
END;
/

/****** Table MeasurementUnit ******/

CREATE TABLE MeasurementUnit(
	MeasUnitID VARCHAR2(50 CHAR) NOT NULL,
	MeasName VARCHAR2(50 CHAR),
	UnitSymbol VARCHAR2(10 CHAR),
	Description VARCHAR2(100 CHAR),
	Notes VARCHAR2(3000),
    CONSTRAINT PK_MeasurementUnit PRIMARY KEY (MeasUnitID)
);

--measurement unit: generate ID
CREATE SEQUENCE seq_unit_id START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE TRIGGER trg_unit_id_string
BEFORE INSERT ON MeasurementUnit
FOR EACH ROW
BEGIN
    IF :NEW.UnitID IS NULL THEN
        SELECT 'Unit' || TO_CHAR(seq_unit_id.NEXTVAL)
        INTO :NEW.UnitID
        FROM dual;
    END IF;
END;
/

/****** Table SensorCapability ******/

CREATE TABLE SensorCapability (
    SensorID      VARCHAR2(50 CHAR) NOT NULL,
    UnitID        VARCHAR2(50 CHAR) NOT NULL,
	tolerance     NUMBER(10,4),
	toleranceUnit VARCHAR2(50 CHAR),
    Notes         VARCHAR2(3000 CHAR),
    DateChecked   TIMESTAMP,
    CheckedBy     VARCHAR2(50 CHAR),
    CONSTRAINT PK_SensorCapability PRIMARY KEY (SensorID, UnitID),
    CONSTRAINT FK_SensorCapability_Sensor FOREIGN KEY (SensorID)
        REFERENCES Sensor (SensorID) ON DELETE CASCADE,
    CONSTRAINT FK_SensorCapability_ToleranceUnit FOREIGN KEY (UnitID)
        REFERENCES MeasurementUnit (UnitID) ON DELETE SET NULL
);

/****** Table SensorCapabilityCheck ******/

CREATE TABLE SensorCapabilityCheck (
    SensorID     VARCHAR2(50 CHAR)   NOT NULL,
    UnitID       VARCHAR2(50 CHAR)   NOT NULL,
    DateChecked  TIMESTAMP NOT NULL,
    Notes        VARCHAR2(3000 CHAR),
	CheckedBy    VARCHAR2(50 CHAR),
    
    CONSTRAINT PK_SensorCapabilityArchive PRIMARY KEY (SensorID, UnitID, DateChecked),
    
    CONSTRAINT FK_SensorCapabilityArchive_Sensor FOREIGN KEY (SensorID)
        REFERENCES Sensor(SensorID) ON DELETE CASCADE,
        
    CONSTRAINT FK_SensorCapabilityArchive_Unit FOREIGN KEY (UnitID)
        REFERENCES MeasurementUnit(UnitID) ON DELETE CASCADE,

	CONSTRAINT FK_SensorCapability_CheckedBy FOREIGN KEY (CheckedBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- archive sensor capability checks (e.g. calibration)
CREATE OR REPLACE TRIGGER trg_sensorcapability_archive
AFTER UPDATE ON SensorCapability
FOR EACH ROW
BEGIN
	IF (
		NVL(:OLD.Notes, '¤') != NVL(:NEW.Notes, '¤') OR
		NVL(:OLD.DateChecked, TO_DATE('1900-01-01', 'YYYY-MM-DD')) != NVL(:NEW.DateChecked, TO_DATE('1900-01-01', 'YYYY-MM-DD'))
	) THEN
    INSERT INTO SensorCapabilityCheck (
        SensorID,
        UnitID,
        DateChecked,
        Notes,
        CheckedBy
    )
    VALUES (
        :OLD.SensorID,
        :OLD.UnitID,
        SYSTIMESTAMP,
        :OLD.Notes,
        :OLD.CheckedBy
    );
	END IF;
END;
/

/****** Table Measurement ******/

-- note organisation index (Oracle specific) to speed data retrieval / analytical operations
CREATE TABLE Measurement (
    SensorID  VARCHAR2(50 CHAR) NOT NULL,
    UnitID    VARCHAR2(50 CHAR) NOT NULL,
    DateTime  TIMESTAMP NOT NULL,
    DateTimePlus6 TIMESTAMP,
    Reading   NUMBER(10,4),
    PRIMARY KEY (SensorID, UnitID, DateTime),
	CONSTRAINT FK_Measurement_SensorCapability FOREIGN KEY (SensorID,UnitID)
        REFERENCES SensorCapability (SensorID,UnitID) ON DELETE CASCADE
	
) ORGANIZATION INDEX;

CREATE INDEX idx_measurement_plus6 ON Measurement(DateTimePlus6);

-- populate the "time plus 6 minutes" at the recording of a new measurement
CREATE OR REPLACE TRIGGER trg_measurement_plus6
BEFORE INSERT ON Measurement
FOR EACH ROW
BEGIN
    IF :NEW.DateTimePlus6 IS NULL THEN
        :NEW.DateTimePlus6 := :NEW.DateTime + INTERVAL '6' MINUTE;
    END IF;
END;
/

/****** Table MeasurementNote ******/

CREATE TABLE MeasurementNote (
    SensorID        VARCHAR2(50 CHAR) NOT NULL,
    UnitID          VARCHAR2(50 CHAR) NOT NULL,
    DateTimeFrom    TIMESTAMP NOT NULL,
    MeasNoteNumber  INTEGER NOT NULL,
    DateTimeTo      TIMESTAMP,
    Notes           VARCHAR2(3000 CHAR),
    MadeBy          VARCHAR2(50 CHAR),
    PRIMARY KEY (SensorID, UnitID, DateTimeFrom, MeasNoteNumber),
    FOREIGN KEY (SensorID, UnitID, DateTimeFrom)
        REFERENCES Measurement (SensorID, UnitID, DateTime)
        ON DELETE CASCADE,
	CONSTRAINT FK_MadeBy FOREIGN KEY (MadeBy)
        REFERENCES AppUser (UserID) ON DELETE SET NULL
);

-- MeasurementNote: generate ID
CREATE OR REPLACE TRIGGER trg_meas_note_number
BEFORE INSERT ON MeasurementNote
FOR EACH ROW
BEGIN
    IF :NEW.MeasNoteNumber IS NULL THEN
        SELECT NVL(MAX(MeasNoteNumber), 0) + 1
        INTO :NEW.MeasNoteNumber
        FROM MeasurementNote
        WHERE SensorID = :NEW.SensorID
          AND UnitID = :NEW.UnitID
          AND DateTimeFrom = :NEW.DateTimeFrom;
    END IF;
END;
/

