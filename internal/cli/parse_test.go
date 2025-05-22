package cli

import (
	"encoding/json"
	"testing"
)

func TestUpParsing(t *testing.T) {
	out, err := Execute([]string{"--region", "us-west-2", "--profile", "default", "--dry-run", "up", "--instance-type", "t3.micro", "--spot", "--ssm", "--run-id", "123"})
	if err != nil {
		t.Fatalf("execute failed: %v", err)
	}
	var data map[string]interface{}
	if err := json.Unmarshal([]byte(out), &data); err != nil {
		t.Fatalf("json parse: %v", err)
	}
	keys := []string{"action", "region", "profile", "dry_run", "instance_type", "spot", "ssm", "run_id"}
	for _, k := range keys {
		if _, ok := data[k]; !ok {
			t.Errorf("missing key %s", k)
		}
	}
}

func TestDownParsing(t *testing.T) {
	out, err := Execute([]string{"--region", "us-east-1", "down"})
	if err != nil {
		t.Fatalf("execute failed: %v", err)
	}
	var data map[string]interface{}
	if err := json.Unmarshal([]byte(out), &data); err != nil {
		t.Fatalf("json parse: %v", err)
	}
	if data["action"] != "down" {
		t.Errorf("expected action down")
	}
}
