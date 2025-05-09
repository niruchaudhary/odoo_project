/** @odoo-module **/

import { ListController } from '@web/views/list/list_controller';
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";


export class CustomListController extends ListController {
    /**
     
Validate all the records selected*/
   setup(){
      super.setup();
      this.orm = useService("orm");
      this.dialog = useService("dialog");}
   async onCustomReturnAction() {
        // Trigger the wizard for CSV upload
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'csv.import.wizard',
            views: [[false, 'form']],
            view_mode: 'form',
            name: 'Import CSV',
            target: 'new',
        });
    }
   async onCustomReturnFunction() {
    try {
        const action = await this.orm.call(
            'e.defter',
            'generate_e_defter_button',
            [[]],
            {}
        );

        console.log("Returned Action:", action);

        if (action) {
            console.log('action..........................',action)
            this.actionService.doAction(action);
        } else {
            console.log('else>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        }
    } catch (error) {
        console.error("Error in Custom Button:", error);
    }
}

}

registry.category('views').add('list_view_button', {
    ...listView,
    Controller: CustomListController,
    buttonTemplate: 'Custom.ListView.Buttons',
});