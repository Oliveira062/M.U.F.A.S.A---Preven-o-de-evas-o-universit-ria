CREATE INDEX IF NOT EXISTS ix_auditoria_requisicao ON auditoria_acessos (id_requisicao);
CREATE INDEX IF NOT EXISTS ix_logs_tecnicos_requisicao ON logs_tecnicos (id_requisicao);
