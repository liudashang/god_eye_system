function api_result(data){
    if(data.error==1){
        toastr.warning(data.info);
        return false;
    }else{
        toastr.success(data.info);
        return true;
    }
}