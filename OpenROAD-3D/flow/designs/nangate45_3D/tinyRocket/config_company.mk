export DESIGN_NAME = ExampleRocketSystem
export DESIGN_NICKNAME = tinyRocket
export PLATFORM = nangate45_3D
export INPUT_DEF = $(COMPANY_3D_DEF)
export IDEAL_CLOCK = 1

export SDC_FILE = ./designs/$(PLATFORM)/tinyRocket/tinyRocket.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/fakeram45_64x32.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_1024x32.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x32.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_1024x32.bottom.lef

export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_64x32.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_1024x32.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x32.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_1024x32.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib

export DIE_AREA = 0 0 1000 1000
export CORE_AREA = 0 0 1000 1000
export TNS_END_PERCENT = 100
export SKIP_GATE_CLONING = 1
include ./designs/nangate45_3D/config_company_route_modes.mk
