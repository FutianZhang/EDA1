variable img_display_name {
  type = string
  default = "almalinux-9.4-20240805"
}

variable namespace {
  type = string
  default = "ucabffz-comp0235-ns"
}

variable network_name {
  type = string
  default = "ucabffz-comp0235-ns/ds4eng"
}

variable username {
  type = string
  default = "ucabffz"
}

variable keyname {
  type = string
  default = "ucabffz"
}

variable vm_count {
  type    = number
  default = 3
}

variable lecturer_public_key_path {
  type = string
  default = "lecturer_key.pub"
}