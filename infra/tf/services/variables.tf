variable "resource_group_location" {
  type        = string
  default     = "swedencentral"
  description = "Location of the resource group."
}

# henk.koht/ projekti kohtainen muuttuja.
variable "identifier" {
  type        = string
  description = "identifier, erottelee taas opiskelijat toisistaan."
  default     = "mikko"
}

# Resurssien nimeämiseen käytettävä muuttuja.
variable "course_short_name" {
  type        = string
  default     = "olearn"
  description = "The short name of the course. This is used in the naming of the resources."

}

variable "default_tags" {
  type        = map(string)
  description = "Default tags that are applied to all resources."
  default = {
    Owner       = "KAMK"
    Environment = "student"
    CostCenter  = "1020"
    Course      = "TT00CC66-3002"
  }
}

variable "frontend_image" {
  type        = string
  description = "The image to use for the frontend container (The Draw Hello Streamlit UI)."
  default     = "crmikkoolearn.azurecr.io/drawhello:1.0" # cropeolearn.azurecr.io/drawhello:1.0
}

# variable "backend_image" {
#   type        = string
#   description = "The image to use for the backend container (The Predict Hello Fast API)"
#   default     = "crmikkoolearn.azurecr.io/predicthello:1.0" # cropeolearn.azurecr.io/predicthello:1.0

# }

# variable "modeller_image" {
#   type        = string
#   description = "The image to use for the modeller container (The Scikit Learn Modeller)"
#   default     = "crmikkoolearn.azurecr.io/modeller:1.0" #  cropeolearn.azurecr.io/modeller:1.0
# }

variable "use_azure_credential" {
  type    = bool
  default = false
}
