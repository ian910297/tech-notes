# JTAG & OPENOCD & RISC-V DEBUGGER
###### tags: `Andes`
* 參考資料
    * RISCV SPEC
        * [Volume 1, Unprivileged Spec v. 20191213](https://riscv.org/specifications/isa-spec-pdf/)
        * [Volume 2, Privileged Spec v. 20190608](https://riscv.org/specifications/privileged-isa/)
        * [External Debug Support v. 0.13.2](https://riscv.org/specifications/debug-specification/)
    * [系統架構秘辛：了解RISC-V 架構底層除錯器的秘密！ 系列](https://ithelp.ithome.com.tw/users/20107327/ironman/1359)
    * [Hellosun](https://ithelp.ithome.com.tw/users/20107327/profile) (公司可靠的大前輩)
    * [Little Robot Studio: JTAG](http://lirobo.blogspot.com/2015/11/jtag.html)
    * [riscv/openocd](https://github.com/riscv/riscv-openocd/)

工作了一段時間，好像都沒仔細講過 OpenOCD 到底是在做些什麼，今天就用一篇文章介紹什麼是 JTAG ？ 而這跟 OpenOCD 又有些什麼關聯？

## 基礎知識介紹

* RISC-V
    一個開源 risc 系列的 ISA，這開源並不是指你們家公司 CPU 內部怎麼作，要把 Verilog 公開出來，而是只有 ISA 是開源的，這邊就可以對照到參考資料的 Spec 部分，想辦法讓做出來的 CPU 符合這些 Spec 就對了
    
    BTW 這系列目前的業界龍頭是 [SiFive](https://en.wikipedia.org/wiki/SiFive)，RISC-V 就是 UCB 推出來的 CPU，而 [SiFive](https://en.wikipedia.org/wiki/SiFive) 就是 UCB 的人出來開的公司，背後也有一堆人投資，比如高通
    
    雖然 Andes Technology 背後也是有 MTK 跟以前矽島計畫的國發基金支持，但總歸要打贏 RISC-V 的親兒子，真的很難說！？好在這塊目前也沒什麼公司在做，比上不足比下有餘啦

* JTAG(Joint Test Action Group)
    一個 Protocol，主要用來測試電路板的元件有沒有問題，一個 bit 一個 bit 打進入測試

* OpenOCD
    一個 Framework ，像是各種 Interface / Protocol 實作的集合體，看到 openocd 的專案資料夾，可以發現依照不同的 protocol，開了一堆資料夾，但我們一般會需要修改的部分只有 target~~~
    
    ![](https://i.imgur.com/UiydNz8.png)
    
    * target/riscv
        符合各種 target 的實作，riscv 只需要看 riscv 資料夾的實作即可
    * rtos
        管理多線呈的簡易系統
    * jtag
        各家 Adapter 的 jtag 實作，如果你的 JTAG 也是從 USB 接出來的，八成就是用 FTDI 這間公司使用 MPSSE 技術實作的程式碼
    * 其他我根本沒改過@@


## JTAG

要介紹最基礎的 JTAG，只要看兩個東西就夠了，四種訊號以及一個狀態機

![](https://i.imgur.com/LyOdvn4.png)

我們可以看到這個狀態機總共有 16 種狀態，起點則是 Run-Test / Idle，IR 則是指 Instruction Register，DR 是指 Data Register，他們的狀態基本上是對應的，只是你必須要先在 IR 下完指令，再去 DR 的狀態準備接收資料，那訊號是怎麼在這狀態機上使用呢？

* Signal
    * TCK (Test Clock)
        運作時 的 clock
    * TDO (Test Data Out)
        從 Host(本機端) 輸出到 Target (板子 ex: FPGA) 的資料
    * TDI (Test Data In)
        從 Target 輸入到 Host 的資料
    * TMS (Test Mode Select)
        狀態轉移作使用的訊號，在這狀態機上的 0/1 皆是指 TMS

那這到底要怎麼使用呢？？？比如說我們現在要下一個指令，那就必須先在 TMS 的部分打入 `1100`，進入 Shift-IR 的狀態，這邊 TMS 只需要不斷的輸入 `0`，然後就可以從 TDO 把想要輸入的指令依序打入

或許會有個疑問，輸入 TMS 跟輸出 TDO 又或者是 TCK，這些訊號是同時進行的嗎？？？沒錯，是同時進行的，一個 TCK 就可以輸入一個 TMS，65536 個 Byte 的 TDO 及 TDI ！？ 反正就是一個很大的數字，很夠用

那讓我們把一個指令的執行分成幾個步驟來看
1. TMS `1100` 移動到 Shift-IR 的狀態
2. TMS 不斷輸入 `0` TDO `輸入想要的指令`
3. TMS `xxxx` 移動回 Run-Test/Idle，在此稍等一下，確定 Instruction 已經就定位，類似 NOP 的功能
4. TMS `100` 移動到 Shift-DR 的狀態
5. TMS 不斷輸入 `0` TDO `輸入對應參數` TDI `取得執行結果`

因為一個指令通常會有對應的參數，只需要在 Shift-DR 時從 TDO 打入即可，到這邊我們已經很清楚的知道 TCK, TDO, TDI, TMS 的功能，以及要輸入指令，執行指令都是在 Shift-IR/DR 的狀態，至於其他沒使用到的狀態，根據不同的硬體有不同的作用，像是有些東西是會在 Update-DR/IR 的時候才觸發。

## OpenOCD 中的實作

對照到 RISC-V 的 Debugger Spec，可以發現 Target 跟 JTAG 溝通是先經過 DTM 再走 DMI

![](https://i.imgur.com/HOpISfN.png)

DTM 的部分會在 examine 時進行確認，確認 DTM 是否正常運作，接下來就不太會去管他了

examine 則是指 initial 完時，開始檢測 Target 是否有任何異常，而 Access 一個 Target 最重要的就是先確認 DTM 有沒有活著，死掉了後面的動作都不用做了

那我們可以把 dtmcontrol_scan 拆分成幾個步驟
1. jtag_add_ir_scan: 移動到 Shift-IR 且設定 Instruction 為 DTM
2. jtag_add_dr_scan: 移動到 Shift-DR 取得目前 DTM 的數值
3. select_dmi: 移動到 Shift-IR 且設定 Instruction 為 DMI
4. jtag_execute_queue: 以上三步驟其實還沒執行 JTAG，所有的東西都被放在一個 Queue 裡面，要等到呼叫 execute_queue 才會執行


* [src/target/riscv/riscv-013.c#L424](https://github.com/riscv/riscv-openocd/blob/riscv/src/target/riscv/riscv-013.c#L424)
```clike=424
static uint32_t dtmcontrol_scan(struct target *target, uint32_t out)
{
	struct scan_field field;
	uint8_t in_value[4];
	uint8_t out_value[4];

	if (bscan_tunnel_ir_width != 0)
		return dtmcontrol_scan_via_bscan(target, out);

	buf_set_u32(out_value, 0, 32, out);

	jtag_add_ir_scan(target->tap, &select_dtmcontrol, TAP_IDLE);

	field.num_bits = 32;
	field.out_value = out_value;
	field.in_value = in_value;
	jtag_add_dr_scan(target->tap, 1, &field, TAP_IDLE);

	/* Always return to dmi. */
	select_dmi(target);

	int retval = jtag_execute_queue();
	if (retval != ERROR_OK) {
		LOG_ERROR("failed jtag scan: %d", retval);
		return retval;
	}

	uint32_t in = buf_get_u32(field.in_value, 0, 32);
	LOG_DEBUG("DTMCS: 0x%x -> 0x%x", out, in);

	return in;
}
```

* [src/target/riscv/riscv-013.c#L1562](https://github.com/riscv/riscv-openocd/blob/riscv/src/target/riscv/riscv-013.c#L1562)
```clike=1562
static int examine(struct target *target)
{
	/* Don't need to select dbus, since the first thing we do is read dtmcontrol. */

	uint32_t dtmcontrol = dtmcontrol_scan(target, 0);
	LOG_DEBUG("dtmcontrol=0x%x", dtmcontrol);
	LOG_DEBUG("  dmireset=%d", get_field(dtmcontrol, DTM_DTMCS_DMIRESET));
	LOG_DEBUG("  idle=%d", get_field(dtmcontrol, DTM_DTMCS_IDLE));
	LOG_DEBUG("  dmistat=%d", get_field(dtmcontrol, DTM_DTMCS_DMISTAT));
	LOG_DEBUG("  abits=%d", get_field(dtmcontrol, DTM_DTMCS_ABITS));
	LOG_DEBUG("  version=%d", get_field(dtmcontrol, DTM_DTMCS_VERSION));
```


一道指令的執行對應到程式碼會是如下所是，可以簡單看為三個步驟

1. select_dmi: 565 行，進入 Shift-IR 且設定 Instruction 為 DMI
2. dmi_scan: 593 行，進入 Shift-IR 從 TDO 輸入對應的參數
3. dmi_scan: 619 行，從 TDI 取得前一個指令執行的結果

dmi_scan 會被放在 while loop 中是因為可能會處於 busy 狀態，需要給他一定的次數重複嘗試

* [src/target/riscv/riscv-013.c#L415](https://github.com/riscv/riscv-openocd/blob/riscv/src/target/riscv/riscv-013.c#L415)
```clike=415
static void select_dmi(struct target *target)
{
	if (bscan_tunnel_ir_width != 0) {
		select_dmi_via_bscan(target);
		return;
	}
	jtag_add_ir_scan(target->tap, &select_dbus, TAP_IDLE);
}
```


* [src/target/riscv/riscv-013.c#L561](https://github.com/riscv/riscv-openocd/blob/riscv/src/target/riscv/riscv-013.c#L561)
```clike=561
static int dmi_op_timeout(struct target *target, uint32_t *data_in,
		bool *dmi_busy_encountered, int dmi_op, uint32_t address,
		uint32_t data_out, int timeout_sec, bool exec, bool ensure_success)
{
	select_dmi(target);

	dmi_status_t status;
	uint32_t address_in;

	if (dmi_busy_encountered)
		*dmi_busy_encountered = false;

	const char *op_name;
	switch (dmi_op) {
		case DMI_OP_NOP:
			op_name = "nop";
			break;
		case DMI_OP_READ:
			op_name = "read";
			break;
		case DMI_OP_WRITE:
			op_name = "write";
			break;
		default:
			LOG_ERROR("Invalid DMI operation: %d", dmi_op);
			return ERROR_FAIL;
	}

	time_t start = time(NULL);
	/* This first loop performs the request.  Note that if for some reason this
	 * stays busy, it is actually due to the previous access. */
	while (1) {
		status = dmi_scan(target, NULL, NULL, dmi_op, address, data_out,
				exec);
		if (status == DMI_STATUS_BUSY) {
			increase_dmi_busy_delay(target);
			if (dmi_busy_encountered)
				*dmi_busy_encountered = true;
		} else if (status == DMI_STATUS_SUCCESS) {
			break;
		} else {
			LOG_ERROR("failed %s at 0x%x, status=%d", op_name, address, status);
			return ERROR_FAIL;
		}
		if (time(NULL) - start > timeout_sec)
			return ERROR_TIMEOUT_REACHED;
	}

	if (status != DMI_STATUS_SUCCESS) {
		LOG_ERROR("Failed %s at 0x%x; status=%d", op_name, address, status);
		return ERROR_FAIL;
	}

	if (ensure_success) {
		/* This second loop ensures the request succeeded, and gets back data.
		 * Note that NOP can result in a 'busy' result as well, but that would be
		 * noticed on the next DMI access we do. */
		while (1) {
			status = dmi_scan(target, &address_in, data_in, DMI_OP_NOP, address, 0,
					false);
			if (status == DMI_STATUS_BUSY) {
				increase_dmi_busy_delay(target);
				if (dmi_busy_encountered)
					*dmi_busy_encountered = true;
			} else if (status == DMI_STATUS_SUCCESS) {
				break;
			} else {
				if (data_in) {
					LOG_ERROR("Failed %s (NOP) at 0x%x; value=0x%x, status=%d",
							op_name, address, *data_in, status);
				} else {
					LOG_ERROR("Failed %s (NOP) at 0x%x; status=%d", op_name, address,
							status);
				}
				return ERROR_FAIL;
			}
			if (time(NULL) - start > timeout_sec)
				return ERROR_TIMEOUT_REACHED;
		}
	}

	return ERROR_OK;
}
```


至於 JTAG 中的實作我就不介紹了，有興趣可以參照 [src/jtag/drivers/ftdi.c](https://github.com/riscv/riscv-openocd/blob/riscv/src/jtag/drivers/ftdi.c) 以及 [src/jtag/drivers/mpsse.c](https://github.com/riscv/riscv-openocd/blob/riscv/src/jtag/drivers/mpsse.c)