terraform {
  required_providers {
    snowflake = {
      source = "snowflakedb/snowflake"
    }
  }
}

# A simple configuration of the provider with a default authentication.
# A default value for `authenticator` is `snowflake`, enabling authentication with `user` and `password`.
provider "snowflake" {
  organization_name = "XATDYDZ" # required if not using profile. Can also be set via SNOWFLAKE_ORGANIZATION_NAME env var
  account_name      = "NF59370" 
  user              = "NGUYENLE98"
}

variable "env" {
  type        = string
  description = "Environment: Prod, UAT, DEV"
}


resource "snowflake_database" "capstone" {
  name = "CAPSTONE_DB_${upper(var.env)}"
}

resource "snowflake_schema" "schema" {
  name     = "RAW"
  database = resource.snowflake_database.capstone.name
}

resource "snowflake_view" "live_rates" {
  database  = resource.snowflake_database.capstone.name
  schema    = resource.snowflake_schema.schema.name
  name      = "LIVE_RATES"
  statement = <<-SQL
    select * from CAPSTONE_FINAL.RAW.LIVE_RATES;
SQL
}