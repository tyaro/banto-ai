/* SDK layout/constant observation only. No Mach call or target memory read. */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/vm_region.h>
#include <stddef.h>
#include <stdio.h>

#define FIELD(name) printf("\"%s\":%zu,", #name, offsetof(vm_region_submap_info_data_64_t, name))
int main(void) {
    printf("{\"sizes\":{\"region\":%zu,\"natural_t\":%zu,\"mach_msg_type_number_t\":%zu,"
           "\"mach_vm_address_t\":%zu,\"mach_vm_size_t\":%zu,\"vm_map_read_t\":%zu,"
           "\"kern_return_t\":%zu,\"memory_object_offset_t\":%zu,\"vm_object_id_t\":%zu},",
           sizeof(vm_region_submap_info_data_64_t),sizeof(natural_t),sizeof(mach_msg_type_number_t),
           sizeof(mach_vm_address_t),sizeof(mach_vm_size_t),sizeof(vm_map_read_t),
           sizeof(kern_return_t),sizeof(memory_object_offset_t),sizeof(vm_object_id_t));
    printf("\"constants\":{\"info_count\":%u,\"read\":%d,\"execute\":%d,\"success\":%d},\"offsets\":{",
           (unsigned)VM_REGION_SUBMAP_INFO_COUNT_64,VM_PROT_READ,VM_PROT_EXECUTE,KERN_SUCCESS);
    FIELD(protection); FIELD(max_protection); FIELD(inheritance); FIELD(offset);
    FIELD(user_tag); FIELD(pages_resident); FIELD(pages_shared_now_private); FIELD(pages_swapped_out);
    FIELD(pages_dirtied); FIELD(ref_count); FIELD(shadow_depth); FIELD(external_pager); FIELD(share_mode);
    FIELD(is_submap); FIELD(behavior); FIELD(object_id); FIELD(user_wired_count); FIELD(flags);
    FIELD(pages_reusable); FIELD(object_id_full); FIELD(pages_wired); FIELD(wire_tag);
    printf("\"__padding0\":%zu}}\n",offsetof(vm_region_submap_info_data_64_t,__padding0));
    return 0;
}
