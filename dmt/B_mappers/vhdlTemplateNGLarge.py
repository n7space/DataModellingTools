# Company: GMV
# Copyright European Space Agency, 2019-2020

vhd = '''
-------------------------------------------------------
--! @file       apb_taste.vhd
--! @brief      PoC APB interface to a TASTE IP
--! @author     Thomas Makryniotis (ESA) 
--!
--!-----------------------------------------------------------------------------------------------
--! @details  
--!  
--! @todo provide a detailed description and comments tag for this entity for doxygen
--!
--! Limitations : None
--!
-------------------------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.ApbPkg.all;

entity apb_taste is
  port (
    pclk : in std_logic;
    presetn : in std_logic;

    s_apb_master : in ApbMasterType;
    s_apb_slave : out ApbSlaveType

    --LEDS_N_O : out std_logic;

    --DBGDONE : out std_logic;
    --DONEBLDBG : out std_logic;
    --STARTDBG : out std_logic
  );
end apb_taste;

architecture rtl of apb_taste is

  type state is (IDLE,
                 WORKING,
                 FIN);

  signal current_state, next_state : state;

  -- Register index

  -----------------------------------
  %(ioregisterindex)s
  -----------------------------------

  -- Register signals

  -----------------------------------
  %(iregistersignals)s
  %(oregistersignals)s
  -----------------------------------

  %(internalstartdone)s

  %(internaloutputs)s

  %(internalsignals)s

begin --Begin architecture 'struct'

%(connectionsToIP)s

  -- Split the following process into two processes, one solely for the registers
  -- and one for the combinational logic
  proc_apb_access : process (all)
  begin

    if presetn = '0' then
      s_apb_slave <= C_APB_SLAVE_INIT;

    elsif rising_edge(pclk) then

      -- Begin default assignments
      
      %(inputregdefaults)s

      led_reg_d <= led_reg_q;
      start_reg <= '0';

      s_apb_slave.pready <= '0';
      s_apb_slave.pslverr <= '0';
      s_apb_slave.prdata <= (others => '0');

      if (s_apb_master.psel and s_apb_master.penable) then
        s_apb_slave.pready <= '1';

        -- Write
        if (s_apb_master.pwrite) = '1' then
          case to_integer(unsigned(s_apb_master.paddr(5 downto 2))) is
          
            when START =>
              start_reg <= s_apb_master.pwdata(0);
            %(apbwriteregs)s
            --! Add TEST register!
            when others =>
              s_apb_slave.pslverr <= '1';
          end case;
        else
          --Read
          case to_integer(unsigned(s_apb_master.paddr(5 downto 2))) is
            when START =>
              s_apb_slave.prdata <= X"000000" & "0000000" & start_reg; -- Doesn't work but will fix it
            
            -- Input registers is posible to be read for sanity purposes

            %(apbreadregs)s 
            when DONE =>
              s_apb_slave.prdata <= X"000000" & "0000000" & reg_done;
            --when TEST =>
            --  s_apb_slave.prdata <= X"0000000" & "000" & led_reg_q;
            when others =>
              s_apb_slave.pslverr <= '1';
          end case;
        end if;
      end if;
    end if;
  end process;

  --! Next state logic
  process (presetn, pclk)
  begin
    if (presetn = '0') then
      current_state <= IDLE;
    elsif (rising_edge(pclk)) then
      current_state <= next_state;
    end if;
  end process;

  --! Current state logic
  process (all)
  begin

    next_state <= current_state;

    case current_state is

      when IDLE =>
        if (start_reg = '1' and %(intipdone)s = '0') then
          next_state <= WORKING;
        end if;

      when WORKING =>
        if (%(intipdone)s = '1') then
          next_state <= FIN;
        end if;

      when FIN =>
        -- We are here because of adder_done. But now it's off again, so we need to keep it in a register.
        reg_done <= '1';
        %(finstateoutputs)s
        if (%(intipstart)s = '1') then
          reg_done <= '0';
          next_state <= WORKING;
        end if;

    end case;

  end process;

  --! Start register process
  start_reg_proc : process (presetn, pclk)
  begin
    if presetn = '0' then
      %(intipstart)s <= '0';
    elsif rising_edge(pclk) then
      %(intipstart)s <= start_reg;
      if (%(intipstart)s = '1' and start_reg = '1') then
        %(intipstart)s <= '0';
      end if;

    end if;
  end process;

  proc_reg : process (pclk, presetn)
  begin
    if presetn = '0' then
      %(regresets)s
      led_reg_q <= '1';
    elsif rising_edge(pclk) then
      %(regclocked)s
      led_reg_q <= led_reg_d;
    end if;
  end process;

  -- Debug process
  -- eq_proc : process (all)
  -- begin
  --   if presetn = '0' then
  --     equals <= '0';
  --   elsif rising_edge(pclk) then
  --     if(reg_done = '1') then
  --       if((X"00000000" & inp0_reg_q) = int_outp) then
  --         equals <= '1';
  --       else
  --         equals <= '0';
  --       end if;
  --     end if;
  --   end if;
  -- end process;

  -- LEDS_N_O <= led_reg_q;
  -- DBGDONE <= reg_done;
  -- DONEBLDBG <= equals;
  -- STARTDBG <= adder_start;

end rtl;'''

makefile = r'''
SRCS=../ip/src/TASTE_AXI.vhd ../ip/src/%(pi)s
EXEC=./TASTE/TASTE.runs/impl_1/TASTE_wrapper.bit

all: ${EXEC}
    
${EXEC}: ${SRCS}
	vivado -mode batch -source TASTE_AXI.tcl

clean:
%(tab)srm -rf *.bit
'''

load_exec = r'''
#! /bin/bash

#Get the programming script path
TCL_DIR="$( cd "$( dirname "$0" )" >/dev/null 2>&1 && pwd )"
#Call the script 
/tools/Xilinx/Vivado/2019.2/bin/xsdb $TCL_DIR/programming.tcl $TCL_DIR $1
'''

programming_tcl = r'''
set host_ip 172.22.71.42
set host_port 3121

set path [lindex $argv 0]

cd $path

puts -nonewline "Connecting to ${host_ip}:${host_port}..."
connect -host 172.22.71.42 -port 3121
puts "OK!"
targets
targets 2
puts -nonewline "Reset the system..."
rst -system
puts "OK!"
puts "Load FPGA and configuring PS system"
fpga -f TASTE/TASTE.runs/impl_1/TASTE_wrapper.bit
source TASTE/TASTE.srcs/sources_1/bd/TASTE/ip/TASTE_processing_system7_0_0/ps7_init.tcl
ps7_init
ps7_post_config
puts "Load FPGA and configuring PS system OK!"
eval dow [lindex $argv 1]
con 
##Uncomment if it is deseired to run in two targets
##targets 3
##con -addr 0x00404040
puts "Software is running!"
'''


axi_support = r'''
#define ARM_CP15_TEXT_SECTION BSP_START_TEXT_SECTION

#include <bsp.h>
#include <bsp/start.h>
#include <bsp/arm-gic-irq.h>
#include <bsp/arm-cp15-start.h>
#include <bsp/arm-a9mpcore-start.h>


#ifdef ARMV7_CP15_START_DEFAULT_SECTIONS

BSP_START_DATA_SECTION static const arm_cp15_start_section_config zynq_mmu_config_table[] = {
    ARMV7_CP15_START_DEFAULT_SECTIONS,
    {
    .begin = 0xe0000000U,
    .end   = 0xe0200000U,
    .flags = ARMV7_MMU_DEVICE
    }, {
    .begin = 0xf8000000U,
    .end   = 0xf9000000U,
    .flags = ARMV7_MMU_DEVICE
    }, {
    .begin = 0x40000000U,
    .end   = 0xc0000000U,
    .flags = ARMV7_MMU_DEVICE
    }, {
    .begin = 0x00100000U,
    .end   = 0x00400000U,
    .flags = ARMV7_MMU_DEVICE
    }, {
    .begin = 0xfffc0000u,
    .end   = 0xffffffffu,
    .flags = ARMV7_MMU_DEVICE
    }
};

BSP_START_TEXT_SECTION void zynq_setup_mmu_and_cache(void) {
    uint32_t ctrl = arm_cp15_start_setup_mmu_and_cache(
    ARM_CP15_CTRL_A,
    ARM_CP15_CTRL_AFE | ARM_CP15_CTRL_Z
    );

    arm_cp15_start_setup_translation_table_and_enable_mmu_and_cache(
    ctrl,
    (uint32_t *) bsp_translation_table_base,
    ARM_MMU_DEFAULT_CLIENT_DOMAIN,
    &zynq_mmu_config_table[0],
    RTEMS_ARRAY_SIZE(zynq_mmu_config_table)
    );
}

#pragma message ("Memory configurations updated for AXI interfaces")

#endif
'''

per_circuit_vhd = """-- Company: GMV
-- Copyright European Space Agency, 2019-2020

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

%(declaration)s

architecture arch of %(pi)s_bambu is

    -- Declare signals
    signal CLK : std_logic;
    signal RST : std_logic;

    signal state : unsigned(1 downto 0);
begin

    CLK <= clock_%(pi)s;
    RST <= reset_%(pi)s;

    -- Possible clock divider
    process(CLK, RST)
    begin
        if (RST='0') then
            finish_%(pi)s <= '0'; -- or 1?
            state                    <= "00";
            -- outp                     <= (others => '0');
        elsif (CLK'event and CLK='1') then
            case state is
                when "00" =>
                    if start_%(pi)s = '1' then
                        state <= "01";
                        finish_%(pi)s <= '0';
                    end if;
                when "01" =>

                    -----------------------------
                    -- Do your processing here --
                    -----------------------------

                    state <= "10";
                when "10" =>
                    finish_%(pi)s <= '1';
                    state <= "00";
                when others =>
                  state <= "00";
            end case;
        end if;
    end process;

end arch;
"""

component_xml = """<?xml version="1.0" encoding="UTF-8"?>
<spirit:component xmlns:xilinx="http://www.xilinx.com" xmlns:spirit="http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <spirit:vendor>user.org</spirit:vendor>
  <spirit:library>user</spirit:library>
  <spirit:name>TASTE</spirit:name>
  <spirit:version>1.0</spirit:version>
  <spirit:busInterfaces>
    <spirit:busInterface>
      <spirit:name>S_AXIS</spirit:name>
      <spirit:busType spirit:vendor="xilinx.com" spirit:library="interface" spirit:name="axis" spirit:version="1.0"/>
      <spirit:abstractionType spirit:vendor="xilinx.com" spirit:library="interface" spirit:name="axis_rtl" spirit:version="1.0"/>
      <spirit:slave/>
      <spirit:portMaps>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>TDEST</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_TDEST</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>TDATA</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_TDATA</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>TLAST</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_TLAST</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>TVALID</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_TVALID</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>TREADY</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_TREADY</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
      </spirit:portMaps>
    </spirit:busInterface>
    <spirit:busInterface>
      <spirit:name>S_AXI</spirit:name>
      <spirit:busType spirit:vendor="xilinx.com" spirit:library="interface" spirit:name="aximm" spirit:version="1.0"/>
      <spirit:abstractionType spirit:vendor="xilinx.com" spirit:library="interface" spirit:name="aximm_rtl" spirit:version="1.0"/>
      <spirit:slave>
        <spirit:memoryMapRef spirit:memoryMapRef="S_AXI"/>
      </spirit:slave>
      <spirit:portMaps>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>AWADDR</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_AWADDR</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>AWVALID</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_AWVALID</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>AWREADY</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_AWREADY</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>WDATA</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_WDATA</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>WSTRB</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_WSTRB</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>WVALID</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_WVALID</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>WREADY</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_WREADY</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>BRESP</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_BRESP</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>BVALID</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_BVALID</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>BREADY</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_BREADY</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>ARADDR</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_ARADDR</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>ARVALID</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_ARVALID</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>ARREADY</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_ARREADY</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>RDATA</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_RDATA</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>RRESP</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_RRESP</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>RVALID</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_RVALID</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>RREADY</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_RREADY</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
      </spirit:portMaps>
    </spirit:busInterface>
    <spirit:busInterface>
      <spirit:name>S_AXI_ARESETN</spirit:name>
      <spirit:busType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="reset" spirit:version="1.0"/>
      <spirit:abstractionType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="reset_rtl" spirit:version="1.0"/>
      <spirit:slave/>
      <spirit:portMaps>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>RST</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_ARESETN</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
      </spirit:portMaps>
      <spirit:parameters>
        <spirit:parameter>
          <spirit:name>POLARITY</spirit:name>
          <spirit:value spirit:id="BUSIFPARAM_VALUE.S_AXI_ARESETN.POLARITY" spirit:choiceRef="choice_list_9d8b0d81">ACTIVE_LOW</spirit:value>
        </spirit:parameter>
      </spirit:parameters>
    </spirit:busInterface>
    <spirit:busInterface>
      <spirit:name>S_AXIS_ACLK</spirit:name>
      <spirit:busType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="clock" spirit:version="1.0"/>
      <spirit:abstractionType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="clock_rtl" spirit:version="1.0"/>
      <spirit:slave/>
      <spirit:portMaps>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>CLK</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_ACLK</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
      </spirit:portMaps>
      <spirit:parameters>
        <spirit:parameter>
          <spirit:name>ASSOCIATED_BUSIF</spirit:name>
          <spirit:value spirit:id="BUSIFPARAM_VALUE.S_AXIS_ACLK.ASSOCIATED_BUSIF">S_AXIS</spirit:value>
        </spirit:parameter>
        <spirit:parameter>
          <spirit:name>ASSOCIATED_RESET</spirit:name>
          <spirit:value spirit:id="BUSIFPARAM_VALUE.S_AXIS_ACLK.ASSOCIATED_RESET">S_AXIS_ARESETN</spirit:value>
        </spirit:parameter>
      </spirit:parameters>
    </spirit:busInterface>
    <spirit:busInterface>
      <spirit:name>S_AXIS_ACLK</spirit:name>
      <spirit:busType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="clock" spirit:version="1.0"/>
      <spirit:abstractionType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="clock_rtl" spirit:version="1.0"/>
      <spirit:slave/>
      <spirit:portMaps>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>CLK</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXIS_ACLK</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
      </spirit:portMaps>
      <spirit:parameters>
        <spirit:parameter>
          <spirit:name>ASSOCIATED_BUSIF</spirit:name>
          <spirit:value spirit:id="BUSIFPARAM_VALUE.S_AXIS_ACLK.ASSOCIATED_BUSIF">S_AXIS</spirit:value>
        </spirit:parameter>
      </spirit:parameters>
    </spirit:busInterface>
    <spirit:busInterface>
      <spirit:name>S_AXI_ACLK</spirit:name>
      <spirit:busType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="clock" spirit:version="1.0"/>
      <spirit:abstractionType spirit:vendor="xilinx.com" spirit:library="signal" spirit:name="clock_rtl" spirit:version="1.0"/>
      <spirit:slave/>
      <spirit:portMaps>
        <spirit:portMap>
          <spirit:logicalPort>
            <spirit:name>CLK</spirit:name>
          </spirit:logicalPort>
          <spirit:physicalPort>
            <spirit:name>S_AXI_ACLK</spirit:name>
          </spirit:physicalPort>
        </spirit:portMap>
      </spirit:portMaps>
      <spirit:parameters>
        <spirit:parameter>
          <spirit:name>ASSOCIATED_BUSIF</spirit:name>
          <spirit:value spirit:id="BUSIFPARAM_VALUE.S_AXI_ACLK.ASSOCIATED_BUSIF">S_AXI</spirit:value>
        </spirit:parameter>
      </spirit:parameters>
    </spirit:busInterface>
  </spirit:busInterfaces>
  <spirit:memoryMaps>
    <spirit:memoryMap>
      <spirit:name>S_AXI</spirit:name>
      <spirit:addressBlock>
        <spirit:name>reg0</spirit:name>
        <spirit:baseAddress spirit:format="bitString" spirit:resolve="user" spirit:bitStringLength="32">0</spirit:baseAddress>
        <spirit:range spirit:format="long" spirit:resolve="user" spirit:minimum="4096" spirit:rangeType="long">4294967296</spirit:range>
        <spirit:width spirit:format="long" spirit:resolve="user">32</spirit:width>
        <spirit:usage>register</spirit:usage>
      </spirit:addressBlock>
    </spirit:memoryMap>
  </spirit:memoryMaps>
  <spirit:model>
    <spirit:views>
      <spirit:view>
        <spirit:name>xilinx_anylanguagesynthesis</spirit:name>
        <spirit:displayName>Synthesis</spirit:displayName>
        <spirit:envIdentifier>:vivado.xilinx.com:synthesis</spirit:envIdentifier>
        <spirit:language>VHDL</spirit:language>
        <spirit:modelName>TASTE</spirit:modelName>
        <spirit:fileSetRef>
          <spirit:localName>xilinx_anylanguagesynthesis_view_fileset</spirit:localName>
        </spirit:fileSetRef>
        <spirit:parameters>
          <spirit:parameter>
            <spirit:name>viewChecksum</spirit:name>
            <spirit:value>1800fe90</spirit:value>
          </spirit:parameter>
        </spirit:parameters>
      </spirit:view>
      <spirit:view>
        <spirit:name>xilinx_anylanguagebehavioralsimulation</spirit:name>
        <spirit:displayName>Simulation</spirit:displayName>
        <spirit:envIdentifier>:vivado.xilinx.com:simulation</spirit:envIdentifier>
        <spirit:language>VHDL</spirit:language>
        <spirit:modelName>TASTE</spirit:modelName>
        <spirit:fileSetRef>
          <spirit:localName>xilinx_anylanguagebehavioralsimulation_view_fileset</spirit:localName>
        </spirit:fileSetRef>
        <spirit:parameters>
          <spirit:parameter>
            <spirit:name>viewChecksum</spirit:name>
            <spirit:value>1800fe90</spirit:value>
          </spirit:parameter>
        </spirit:parameters>
      </spirit:view>
      <spirit:view>
        <spirit:name>xilinx_xpgui</spirit:name>
        <spirit:displayName>UI Layout</spirit:displayName>
        <spirit:envIdentifier>:vivado.xilinx.com:xgui.ui</spirit:envIdentifier>
        <spirit:fileSetRef>
          <spirit:localName>xilinx_xpgui_view_fileset</spirit:localName>
        </spirit:fileSetRef>
        <spirit:parameters>
          <spirit:parameter>
            <spirit:name>viewChecksum</spirit:name>
            <spirit:value>f92e9879</spirit:value>
          </spirit:parameter>
        </spirit:parameters>
      </spirit:view>
    </spirit:views>
    <spirit:ports>
      <spirit:port>
        <spirit:name>S_AXI_ACLK</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_ARESETN</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_AWADDR</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">31</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_AWVALID</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_AWREADY</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_WDATA</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">31</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_WSTRB</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">3</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">1</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_WVALID</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_WREADY</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_ARADDR</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">31</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_ARVALID</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_ARREADY</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_RDATA</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">31</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_RRESP</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">1</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_RVALID</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_RREADY</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_BRESP</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:vector>
            <spirit:left spirit:format="long">1</spirit:left>
            <spirit:right spirit:format="long">0</spirit:right>
          </spirit:vector>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic_vector</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_BVALID</spirit:name>
        <spirit:wire>
          <spirit:direction>out</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
        </spirit:wire>
      </spirit:port>
      <spirit:port>
        <spirit:name>S_AXI_BREADY</spirit:name>
        <spirit:wire>
          <spirit:direction>in</spirit:direction>
          <spirit:wireTypeDefs>
            <spirit:wireTypeDef>
              <spirit:typeName>std_logic</spirit:typeName>
              <spirit:viewNameRef>xilinx_anylanguagesynthesis</spirit:viewNameRef>
              <spirit:viewNameRef>xilinx_anylanguagebehavioralsimulation</spirit:viewNameRef>
            </spirit:wireTypeDef>
          </spirit:wireTypeDefs>
          <spirit:driver>
            <spirit:defaultValue spirit:format="long">0</spirit:defaultValue>
          </spirit:driver>
        </spirit:wire>
      </spirit:port>
    </spirit:ports>
  </spirit:model>
  <spirit:choices>
    <spirit:choice>
      <spirit:name>choice_list_9d8b0d81</spirit:name>
      <spirit:enumeration>ACTIVE_HIGH</spirit:enumeration>
      <spirit:enumeration>ACTIVE_LOW</spirit:enumeration>
    </spirit:choice>
  </spirit:choices>
  <spirit:fileSets>
    <spirit:fileSet>
      <spirit:name>xilinx_anylanguagesynthesis_view_fileset</spirit:name>
      <spirit:file>
        <spirit:name>src/%(pi)s</spirit:name>
        <spirit:fileType>vhdlSource</spirit:fileType>
        <spirit:userFileType>IMPORTED_FILE</spirit:userFileType>
      </spirit:file>
      <spirit:file>
        <spirit:name>src/TASTE_AXI.vhd</spirit:name>
        <spirit:fileType>vhdlSource</spirit:fileType>
        <spirit:userFileType>CHECKSUM_20a3fb2c</spirit:userFileType>
        <spirit:userFileType>IMPORTED_FILE</spirit:userFileType>
      </spirit:file>
    </spirit:fileSet>
    <spirit:fileSet>
      <spirit:name>xilinx_anylanguagebehavioralsimulation_view_fileset</spirit:name>
      <spirit:file>
        <spirit:name>src/%(pi)s</spirit:name>
        <spirit:fileType>vhdlSource</spirit:fileType>
        <spirit:userFileType>IMPORTED_FILE</spirit:userFileType>
      </spirit:file>
      <spirit:file>
        <spirit:name>src/TASTE_AXI.vhd</spirit:name>
        <spirit:fileType>vhdlSource</spirit:fileType>
        <spirit:userFileType>IMPORTED_FILE</spirit:userFileType>
      </spirit:file>
    </spirit:fileSet>
    <spirit:fileSet>
      <spirit:name>xilinx_xpgui_view_fileset</spirit:name>
      <spirit:file>
        <spirit:name>xgui/TASTE_AXI_v1_0.tcl</spirit:name>
        <spirit:fileType>tclSource</spirit:fileType>
        <spirit:userFileType>CHECKSUM_f92e9879</spirit:userFileType>
        <spirit:userFileType>XGUI_VERSION_2</spirit:userFileType>
      </spirit:file>
    </spirit:fileSet>
  </spirit:fileSets>
  <spirit:description>TASTE_v1_0</spirit:description>
  <spirit:parameters>
    <spirit:parameter>
      <spirit:name>Component_Name</spirit:name>
      <spirit:value spirit:resolve="user" spirit:id="PARAM_VALUE.Component_Name" spirit:order="1">TASTE_v1_0</spirit:value>
    </spirit:parameter>
  </spirit:parameters>
  <spirit:vendorExtensions>
    <xilinx:coreExtensions>
      <xilinx:supportedFamilies>
        <xilinx:family xilinx:lifeCycle="Production">zynq</xilinx:family>
      </xilinx:supportedFamilies>
      <xilinx:taxonomies>
        <xilinx:taxonomy>/UserIP</xilinx:taxonomy>
      </xilinx:taxonomies>
      <xilinx:displayName>TASTE_v1_0</xilinx:displayName>
      <xilinx:definitionSource>package_project</xilinx:definitionSource>
      <xilinx:coreRevision>2</xilinx:coreRevision>
      <xilinx:coreCreationDateTime>2020-03-30T11:10:33Z</xilinx:coreCreationDateTime>
      <xilinx:tags>
        <xilinx:tag xilinx:name="ui.data.coregen.dd@1caba8a6_ARCHIVE_LOCATION">/ip</xilinx:tag>
        <xilinx:tag xilinx:name="ui.data.coregen.dd@54d0a6ec_ARCHIVE_LOCATION">/ip</xilinx:tag>
        <xilinx:tag xilinx:name="ui.data.coregen.dd@3316f770_ARCHIVE_LOCATION">/ip</xilinx:tag>
        <xilinx:tag xilinx:name="ui.data.coregen.dd@7b16f982_ARCHIVE_LOCATION">/ip</xilinx:tag>
        <xilinx:tag xilinx:name="ui.data.coregen.dd@5717d5e9_ARCHIVE_LOCATION">/ip</xilinx:tag>
        <xilinx:tag xilinx:name="ui.data.coregen.dd@5a5ce90d_ARCHIVE_LOCATION">/ip</xilinx:tag>
      </xilinx:tags>
    </xilinx:coreExtensions>
    <xilinx:packagingInfo>
      <xilinx:xilinxVersion>2019.2</xilinx:xilinxVersion>
      <xilinx:checksum xilinx:scope="busInterfaces" xilinx:value="da618e65"/>
      <xilinx:checksum xilinx:scope="memoryMaps" xilinx:value="f2afdf52"/>
      <xilinx:checksum xilinx:scope="fileGroups" xilinx:value="7810a59c"/>
      <xilinx:checksum xilinx:scope="ports" xilinx:value="929b14a0"/>
      <xilinx:checksum xilinx:scope="parameters" xilinx:value="3fe0208c"/>
    </xilinx:packagingInfo>
  </spirit:vendorExtensions>
</spirit:component>"""
