import {
  boolean,
  index,
  integer,
  jsonb,
  pgTable,
  text,
  timestamp,
  uuid,
  varchar,
} from "drizzle-orm/pg-core";

export const mockHospitalDb = pgTable(
  "mock_hospital_db",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    patientId: varchar("patient_id", { length: 128 }).notNull(),
    rawText: text("raw_text").notNull(),
    fileUrl: text("file_url"),
    createdAt: timestamp("created_at", { withTimezone: true })
      .defaultNow()
      .notNull(),
  },
  (t) => [index("mock_hospital_db_patient_id_idx").on(t.patientId)],
);

export const stagingVault = pgTable(
  "staging_vault",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    ingestId: text("ingest_id"),
    patientId: varchar("patient_id", { length: 128 }).notNull(),
    rawPayload: jsonb("raw_payload"),
    fhirJson: jsonb("fhir_json"),
    conflictFlag: boolean("conflict_flag").default(false),
    aiWarningMsg: text("ai_warning_msg"),
    model: text("model"),
    status: varchar("status", { length: 32 }).default("pending").notNull(),
    attempts: integer("attempts").default(0),
    fallbackReason: text("fallback_reason"),
    createdAt: timestamp("created_at", { withTimezone: true })
      .defaultNow()
      .notNull(),
    processedAt: timestamp("processed_at", { withTimezone: true }),
  },
  (t) => [
    index("staging_vault_patient_id_idx").on(t.patientId),
    index("staging_vault_patient_status_idx").on(t.patientId, t.status),
    index("staging_vault_ingest_id_idx").on(t.ingestId),
  ],
);

export const mainVault = pgTable(
  "main_vault",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    patientId: varchar("patient_id", { length: 128 }).notNull(),
    encryptedFhirJsonId: uuid("encrypted_fhir_json_id").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .defaultNow()
      .notNull(),
  },
  (t) => [index("main_vault_patient_id_idx").on(t.patientId)],
);

export const auditLogs = pgTable(
  "audit_logs",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    timestamp: timestamp("timestamp", { withTimezone: true })
      .defaultNow()
      .notNull(),
    adminId: varchar("admin_id", { length: 128 }).notNull(),
    patientId: varchar("patient_id", { length: 128 }).notNull(),
    actionType: varchar("action_type", { length: 64 }).notNull(),
    oldValue: jsonb("old_value"),
    newValue: jsonb("new_value"),
  },
  (t) => [index("audit_logs_patient_id_idx").on(t.patientId)],
);
