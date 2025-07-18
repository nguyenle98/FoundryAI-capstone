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

resource "snowflake_table" "Currency" {
  database                    = "CAPSTONE_FINAL"
  schema                      = "RAW"
  name                        = "DIM_CURRENCY"
  comment                     = "Currency explained"

  column {
    name     = "Currency"
    type     = "string"
    nullable = false

    
  }

  column {
    name     = "CODE"
    type     = "string"
    nullable = false
  }
 
}