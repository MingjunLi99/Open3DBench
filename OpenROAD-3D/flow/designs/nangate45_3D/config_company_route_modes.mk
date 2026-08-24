COMPANY_ROUTE_MODE ?= quick

ifeq ($(COMPANY_ROUTE_MODE),quick)
export DETAILED_ROUTE_ARGS = -droute_end_iter 5
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
else ifeq ($(COMPANY_ROUTE_MODE),quality)
unexport DETAILED_ROUTE_ARGS
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 50
else ifeq ($(COMPANY_ROUTE_MODE),postplace)
unexport DETAILED_ROUTE_ARGS
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
else
$(error Unsupported COMPANY_ROUTE_MODE '$(COMPANY_ROUTE_MODE)'; use quick, quality, or postplace)
endif

export FLOW_VARIANT = company_$(COMPANY_ROUTE_MODE)
